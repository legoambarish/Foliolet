package com.sih26190.dms.bridge;

import com.sih26190.dms.model.*;
import com.sih26190.dms.selective.PrivateVault;
import java.net.*;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.cert.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

@Service
@ConditionalOnProperty(name = "bridge.enabled", havingValue = "true")
public class ImportService {
  private final BridgeItems items;
  private final PrivateVault vault;
  private final Environment env;
  private final TransactionTemplate tx;
  private final Map<String, DocumentProvider> providers;
  private final ExecutorService worker =
      new ThreadPoolExecutor(
          1,
          1,
          0,
          TimeUnit.SECONDS,
          new ArrayBlockingQueue<>(8),
          r -> {
            var t = new Thread(r, "import-validation");
            t.setDaemon(true);
            return t;
          });

  public ImportService(
      BridgeItems items, PrivateVault vault, Environment env, PlatformTransactionManager manager) {
    this.items = items;
    this.vault = vault;
    this.env = env;
    this.tx = new TransactionTemplate(manager);
    this.providers =
        Map.of(
            "mock",
            new MockProvider(),
            "uploaded-xml",
            new UploadProvider(),
            "setu-sandbox",
            new SetuProvider());
  }

  private Map<String, Object> read(BridgeItem i) {
    return BridgeProtocol.parse(vault.open(i.getEncryptedPayload(), i.getId()));
  }

  private void write(BridgeItem i, Map<String, Object> p) {
    i.setEncryptedPayload(vault.seal(BridgeProtocol.stable(p), i.getId()));
    items.saveAndFlush(i);
  }

  private BridgeItem own(User user, String id) {
    var i = items.lock(id).orElseThrow(() -> new IllegalArgumentException("Unknown import"));
    if (!i.getKind().equals("IMPORT") || !i.getOwner().equals(user.getUsername()))
      throw new SecurityException("Import owner required");
    return i;
  }

  private Map<String, Object> view(BridgeItem i) {
    var p = read(i);
    return Map.of(
        "id",
        i.getId(),
        "status",
        i.getStatus(),
        "expiresAt",
        i.getExpiresAt(),
        "provider",
        p.get("provider"),
        "authUrl",
        p.getOrDefault("authUrl", ""),
        "documents",
        p.getOrDefault("documents", List.of()),
        "events",
        p.get("events"),
        "result",
        p.getOrDefault("result", Map.of()),
        "message",
        p.getOrDefault("message", ""));
  }

  private static void event(Map<String, Object> p, String state) {
    ((List<Object>) p.get("events")).add(Map.of("state", state, "at", BridgeService.now()));
  }

  public Map<String, Object> start(User user, Map<String, Object> input) throws Exception {
    BridgeService.role(user, Role.HOLDER);
    String name = BridgeService.text(input, "provider");
    var provider = providers.get(name);
    if (provider == null) throw new IllegalArgumentException("Unsupported import provider");
    String id = org.web3j.crypto.Hash.sha3String(UUID.randomUUID().toString());
    String callback = env.getProperty("bridge.public-base-url", "");
    if (name.equals("setu-sandbox") && !callback.startsWith("https://"))
      throw new IllegalArgumentException("Setu requires a configured stable HTTPS PUBLIC_BASE_URL");
    var transport = provider.start(callback + "/imports/callback/?state=" + id);
    return tx.execute(
        status -> {
          var i = new BridgeItem();
          i.setId(id);
          i.setOwner(user.getUsername());
          i.setKind("IMPORT");
          i.setStatus(name.equals("uploaded-xml") ? "WAITING_UPLOAD" : "WAITING_LOGIN");
          i.setCreatedAt(BridgeService.now());
          i.setExpiresAt(BridgeService.now() + 300);
          var p = new LinkedHashMap<String, Object>();
          p.put("provider", name);
          p.put("session", transport.get("session"));
          p.put("authUrl", transport.getOrDefault("authUrl", ""));
          p.put(
              "events",
              new ArrayList<>(List.of(Map.of("state", i.getStatus(), "at", BridgeService.now()))));
          write(i, p);
          return view(i);
        });
  }

  public Map<String, Object> status(User user, String id) {
    return tx.execute(
        status -> {
          var i = own(user, id);
          if (i.getExpiresAt() <= BridgeService.now()
              && !Set.of("DONE", "FAILED", "CANCELLED", "TIMEOUT").contains(i.getStatus())) {
            var p = read(i);
            i.setStatus("TIMEOUT");
            event(p, "TIMEOUT");
            write(i, p);
          }
          return view(i);
        });
  }

  public Map<String, Object> consent(User user, String id, Map<String, Object> input)
      throws Exception {
    var snapshot =
        tx.execute(
            status -> {
              var i = own(user, id);
              if (i.getExpiresAt() <= BridgeService.now()
                  || !Set.of("WAITING_LOGIN", "WAITING_CONSENT").contains(i.getStatus()))
                throw new IllegalArgumentException("Import cannot accept consent in this state");
              return read(i);
            });
    var provider = providers.get(snapshot.get("provider"));
    String session = snapshot.get("session").toString();
    if (!provider.authenticated(session))
      throw new IllegalArgumentException(
          "Provider has not confirmed authorization; callback flags are not trusted");
    var list = provider.list(session);
    return tx.execute(
        status -> {
          var i = own(user, id);
          if (!Set.of("WAITING_LOGIN", "WAITING_CONSENT").contains(i.getStatus()))
            throw new IllegalArgumentException("Import state changed");
          var p = read(i);
          p.put("documents", list);
          event(p, "WAITING_CONSENT");
          i.setStatus("WAITING_CONSENT");
          write(i, p);
          return view(i);
        });
  }

  public Map<String, Object> fetch(User user, String id, Map<String, Object> selection)
      throws Exception {
    var snapshot =
        tx.execute(
            status -> {
              var i = own(user, id);
              if (!i.getStatus().equals("WAITING_CONSENT")
                  || i.getExpiresAt() <= BridgeService.now())
                throw new IllegalArgumentException("Document consent required");
              var p = read(i);
              i.setStatus("FETCHING_DOCUMENT");
              event(p, i.getStatus());
              write(i, p);
              return p;
            });
    try {
      byte[] bytes =
          providers
              .get(snapshot.get("provider"))
              .fetch(snapshot.get("session").toString(), selection);
      submit(user, id, bytes);
    } catch (Exception e) {
      fail(user, id, "Provider fetch failed; no raw bytes retained");
      throw e;
    }
    return status(user, id);
  }

  public Map<String, Object> xml(User user, Map<String, Object> input) throws Exception {
    String id = BridgeService.text(input, "id"), xml = BridgeService.text(input, "xml");
    byte[] bytes = xml.getBytes(StandardCharsets.UTF_8);
    if (bytes.length > 131072) throw new IllegalArgumentException("XML exceeds 128 KiB");
    tx.executeWithoutResult(
        status -> {
          var i = own(user, id);
          if (!i.getStatus().equals("WAITING_UPLOAD")
              || !read(i).get("provider").equals("uploaded-xml")
              || i.getExpiresAt() <= BridgeService.now())
            throw new IllegalArgumentException("Upload is not expected");
          i.setStatus("FETCHING_DOCUMENT");
          var p = read(i);
          event(p, i.getStatus());
          write(i, p);
        });
    submit(user, id, bytes);
    return status(user, id);
  }

  private void submit(User user, String id, byte[] bytes) {
    try {
      worker.execute(
          () -> {
            try {
              tx.executeWithoutResult(
                  status -> {
                    var i = own(user, id);
                    if (i.getStatus().equals("CANCELLED")
                        || i.getExpiresAt() <= BridgeService.now()) return;
                    var p = read(i);
                    i.setStatus("VERIFYING_SIGNATURE");
                    event(p, i.getStatus());
                    write(i, p);
                  });
              X509Certificate pin = null;
              String certificate = env.getProperty("bridge.import.trusted-certificate", "");
              if (!certificate.isBlank())
                try (var in = Files.newInputStream(Path.of(certificate))) {
                  pin =
                      (X509Certificate)
                          CertificateFactory.getInstance("X.509").generateCertificate(in);
                }
              var result =
                  XmlSourceValidator.inspect(
                      bytes,
                      pin,
                      env.getProperty("bridge.import.trusted-issuer", ""),
                      env.getProperty("bridge.import.trusted-type", ""));
              tx.executeWithoutResult(
                  status -> {
                    var i = own(user, id);
                    if (i.getStatus().equals("CANCELLED")
                        || i.getExpiresAt() <= BridgeService.now()) return;
                    var p = read(i);
                    p.put("result", result);
                    i.setStatus("DONE");
                    event(p, i.getStatus());
                    p.remove("session");
                    write(i, p);
                  });
            } catch (Exception e) {
              fail(
                  user, id, "XML invalid or unsupported trust profile; no imported fact confirmed");
            } finally {
              Arrays.fill(bytes, (byte) 0);
            }
          });
    } catch (RejectedExecutionException e) {
      Arrays.fill(bytes, (byte) 0);
      fail(user, id, "Import worker busy; retry a new import");
    }
  }

  private void fail(User user, String id, String message) {
    tx.executeWithoutResult(
        status -> {
          var i = own(user, id);
          if (i.getStatus().equals("CANCELLED")) return;
          var p = read(i);
          i.setStatus("FAILED");
          p.put("message", message);
          p.remove("session");
          event(p, i.getStatus());
          write(i, p);
        });
  }

  public Map<String, Object> cancel(User user, String id) {
    return tx.execute(
        status -> {
          var i = own(user, id);
          if (Set.of("DONE", "FAILED", "TIMEOUT").contains(i.getStatus()))
            throw new IllegalArgumentException("Import already finished");
          var p = read(i);
          i.setStatus("CANCELLED");
          event(p, i.getStatus());
          p.remove("session");
          write(i, p);
          return view(i);
        });
  }

  public Map<String, Object> confirm(User user, String id) {
    return tx.execute(
        status -> {
          var i = own(user, id);
          if (!i.getStatus().equals("DONE"))
            throw new IllegalArgumentException("Finished import required");
          var p = read(i);
          var result = new LinkedHashMap<>(BridgeService.map(p.get("result")));
          result.put(
              "fields",
              ((List<?>) result.get("fields"))
                  .stream()
                      .map(
                          f -> {
                            var field = new LinkedHashMap<>(BridgeService.map(f));
                            field.put("confirmed", true);
                            return field;
                          })
                      .toList());
          result.put("confirmationAuthority", "HOLDER_REVIEW_ONLY");
          p.put("result", result);
          event(p, "HOLDER_REVIEWED");
          write(i, p);
          return view(i);
        });
  }

  private static class UploadProvider implements DocumentProvider {
    public String name() {
      return "uploaded-xml";
    }

    public Map<String, Object> start(String callback) {
      return Map.of("session", "upload");
    }

    public boolean authenticated(String session) {
      return false;
    }

    public List<Map<String, Object>> list(String session) {
      return List.of();
    }

    public byte[] fetch(String session, Map<String, Object> selection) {
      throw new IllegalArgumentException("Upload XML explicitly");
    }
  }

  private static class MockProvider implements DocumentProvider {
    public String name() {
      return "mock";
    }

    public Map<String, Object> start(String callback) {
      return Map.of("session", UUID.randomUUID().toString());
    }

    public boolean authenticated(String session) {
      return true;
    }

    public List<Map<String, Object>> list(String session) {
      return List.of(
          Map.of(
              "id", "demo-transcript", "name", "MOCK unsigned test transcript", "simulated", true));
    }

    public byte[] fetch(String session, Map<String, Object> selection) {
      if (!"demo-transcript".equals(selection.get("id")))
        throw new IllegalArgumentException("Unknown mock document");
      return "<IssuedDocument issuer=\"Mock University\" type=\"transcript\"><Facts><Fact path=\"education.enrolled\">true</Fact><Fact path=\"education.cgpa\">8.7</Fact></Facts></IssuedDocument>"
          .getBytes(StandardCharsets.UTF_8);
    }
  }

  private class SetuProvider implements DocumentProvider {
    private final HttpClient http =
        HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(8))
            .followRedirects(HttpClient.Redirect.NEVER)
            .build();

    public String name() {
      return "setu-sandbox";
    }

    private Map<String, Object> request(String method, String path, Map<String, Object> body)
        throws Exception {
      String client = env.getProperty("SETU_CLIENT_ID", ""),
          secret = env.getProperty("SETU_CLIENT_SECRET", ""),
          product = env.getProperty("SETU_PRODUCT_INSTANCE_ID", "");
      if (client.isBlank() || secret.isBlank() || product.isBlank())
        throw new IllegalArgumentException("Setu sandbox is disabled: credentials are absent");
      if (!path.matches("/api/digilocker/(?:[a-zA-Z0-9-]{1,100}/(?:status|document))?"))
        throw new IllegalArgumentException("Unsupported provider endpoint");
      var builder =
          HttpRequest.newBuilder(URI.create("https://dg-sandbox.setu.co" + path))
              .timeout(Duration.ofSeconds(25))
              .header("x-client-id", client)
              .header("x-client-secret", secret)
              .header("x-product-instance-id", product)
              .header("Content-Type", "application/json");
      builder.method(
          method,
          body == null
              ? HttpRequest.BodyPublishers.noBody()
              : HttpRequest.BodyPublishers.ofString(BridgeProtocol.stable(body)));
      var response = http.send(builder.build(), HttpResponse.BodyHandlers.ofInputStream());
      try (var stream = response.body()) {
        byte[] bytes = stream.readNBytes(131073);
        if (bytes.length > 131072 || response.statusCode() != 200)
          throw new IllegalArgumentException("Provider rejected request");
        return BridgeProtocol.parse(new String(bytes, StandardCharsets.UTF_8));
      }
    }

    public Map<String, Object> start(String callback) throws Exception {
      var response = request("POST", "/api/digilocker/", Map.of("redirectUrl", callback));
      String url = response.get("url").toString();
      if (!url.startsWith("https://"))
        throw new IllegalArgumentException("Invalid provider authorization URL");
      return Map.of("session", response.get("id"), "authUrl", url);
    }

    public boolean authenticated(String session) throws Exception {
      return "authenticated"
          .equals(request("GET", "/api/digilocker/" + session + "/status", null).get("status"));
    }

    public List<Map<String, Object>> list(String session) {
      return List.of(
          Map.of(
              "name",
              "Configured Setu document specification",
              "docType",
              env.getProperty("SETU_DOCUMENT_TYPE", ""),
              "orgId",
              env.getProperty("SETU_ORG_ID", ""),
              "format",
              "xml",
              "note",
              "Configure an approved document specification; global catalog fetching is"
                  + " intentionally excluded."));
    }

    public byte[] fetch(String session, Map<String, Object> selection) throws Exception {
      if (!authenticated(session))
        throw new IllegalArgumentException("Provider authorization missing");
      String type = env.getProperty("SETU_DOCUMENT_TYPE", ""),
          org = env.getProperty("SETU_ORG_ID", "");
      if (type.isBlank() || org.isBlank())
        throw new IllegalArgumentException("Configure an approved issuer/document specification");
      var response =
          request(
              "POST",
              "/api/digilocker/" + session + "/document",
              Map.of(
                  "docType",
                  type,
                  "orgId",
                  org,
                  "format",
                  "xml",
                  "consent",
                  "Y",
                  "parameters",
                  selection.getOrDefault("parameters", List.of())));
      URI url = URI.create(response.get("fileUrl").toString());
      var hosts = Arrays.asList(env.getProperty("SETU_DOWNLOAD_HOSTS", "").split(","));
      if (!"https".equals(url.getScheme())
          || url.getUserInfo() != null
          || !hosts.contains(url.getHost())
          || url.getPort() > 0 && url.getPort() != 443)
        throw new IllegalArgumentException("Provider download host is not explicitly allowed");
      var downloaded =
          http.send(
              HttpRequest.newBuilder(url).timeout(Duration.ofSeconds(25)).GET().build(),
              HttpResponse.BodyHandlers.ofInputStream());
      try (var stream = downloaded.body()) {
        byte[] bytes = stream.readNBytes(131073);
        if (bytes.length > 131072 || downloaded.statusCode() != 200)
          throw new IllegalArgumentException("Provider file exceeds bound or download failed");
        return bytes;
      }
    }
  }
}
