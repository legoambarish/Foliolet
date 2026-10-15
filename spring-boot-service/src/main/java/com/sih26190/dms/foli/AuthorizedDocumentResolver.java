package com.sih26190.dms.foli;

import com.sih26190.dms.model.*;
import com.sih26190.dms.repository.DocumentRecordRepository;
import com.sih26190.dms.selective.PrivateVault;
import com.sih26190.dms.selective.repository.CredentialDocumentRepository;
import java.nio.file.*;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;
import org.web3j.crypto.Hash;
import org.web3j.utils.Numeric;
import static com.sih26190.dms.foli.FoliData.*;

/** Independent, strictly read-only adapters. No restore, audit-write or chain calls. */
@Service
@Transactional(readOnly = true)
public class AuthorizedDocumentResolver {
  private final CredentialDocumentRepository wallet;
  private final DocumentRecordRepository legacy;
  private final PrivateVault vault;
  private final FoliProperties limits;
  private final Path legacyRoot;

  public AuthorizedDocumentResolver(CredentialDocumentRepository wallet,
      DocumentRecordRepository legacy, PrivateVault vault, FoliProperties limits,
      @Value("${dms.storage.location:../.local-data/legacy/files}") String legacyRoot) {
    this.wallet = wallet; this.legacy = legacy; this.vault = vault; this.limits = limits;
    this.legacyRoot = Path.of(legacyRoot).toAbsolutePath().normalize();
  }

  public List<Document> list(User user) {
    var result = new ArrayList<Document>();
    for (var d : wallet.findByOwnerIdOrderByCreatedAtDesc(user.getId()))
      result.add(metadata("wallet:" + d.id, d.displayName, d.originalFilename,
          d.status, Integer.toString(d.version)));
    var records = user.getRole() == Role.ADMIN ? legacy.findAll() : legacy.findByUploadedBy(user);
    for (var d : records) result.add(metadata("legacy:" + d.getId(),
        d.getOriginalFileName(), d.getOriginalFileName(), "RETAINED", String.valueOf(d.getUploadedAt())));
    return List.copyOf(result);
  }

  public Source open(String typedId, User user) {
    if (typedId == null || typedId.length() > 100) throw missing();
    try {
      Document meta;
      byte[] bytes;
      if (typedId.matches("wallet:(?:0x)?[0-9a-f]{64}")) {
        String id = typedId.substring(7);
        var d = wallet.findById(id).orElseThrow(AuthorizedDocumentResolver::missing);
        if (!Objects.equals(d.ownerId, user.getId())) throw missing();
        safeFile(Path.of(d.filePath), vault.root.resolve("wallet"), limits.getMaxBytes() + 28L);
        bytes = vault.read(d.filePath, d.id);
        if (d.documentHash == null || !Numeric.toHexString(Hash.sha3(bytes)).equals(d.documentHash))
          throw failure("SOURCE_CHANGED", "The retained original differs from its enrolled hash. Foli did not restore or modify it.");
        meta = metadata(typedId, d.displayName, d.originalFilename, d.status, Integer.toString(d.version));
      } else if (typedId.matches("legacy:[1-9][0-9]{0,17}")) {
        var d = legacy.findById(Long.parseLong(typedId.substring(7))).orElseThrow(AuthorizedDocumentResolver::missing);
        if (user.getRole() != Role.ADMIN && (d.getUploadedBy() == null ||
            !Objects.equals(d.getUploadedBy().getId(), user.getId()))) throw missing();
        Path path = safeFile(Path.of(d.getFilePath()), legacyRoot, limits.getMaxBytes());
        bytes = Files.readAllBytes(path);
        meta = metadata(typedId, d.getOriginalFileName(), d.getOriginalFileName(),
            "RETAINED", String.valueOf(d.getUploadedAt()));
      } else throw missing();
      if (bytes.length == 0 || bytes.length > limits.getMaxBytes())
        throw new FoliException(HttpStatus.PAYLOAD_TOO_LARGE, "SOURCE_LIMIT", "Use a nonempty original up to 20 MiB.");
      return new Source(meta, PrivateVault.sha256(bytes), bytes);
    } catch (ResponseStatusException e) { throw e;
    } catch (Exception e) {
      throw failure("SOURCE_UNAVAILABLE", "The private original is missing or could not be authenticated. No recovery was performed.");
    }
  }

  private static Path safeFile(Path file, Path root, long max) throws Exception {
    Path actualRoot = root.toRealPath();
    Path actual = file.toAbsolutePath().normalize().toRealPath();
    if (!actual.startsWith(actualRoot) || !Files.isRegularFile(actual) || Files.size(actual) > max)
      throw new IllegalArgumentException("Unsafe or oversized source");
    return actual;
  }

  static Document metadata(String id, String name, String filename, String status, String version) {
    String safeName = name == null ? "Untitled document" : name;
    String safeFile = filename == null ? "document" : filename;
    int dot = safeFile.lastIndexOf('.');
    String format = dot < 0 ? "unknown" : safeFile.substring(dot + 1).toLowerCase(Locale.ROOT);
    return new Document(id, safeName, safeFile, format, status, version,
        Set.of("pdf", "txt", "csv").contains(format));
  }
  static ResponseStatusException missing() { return new FoliException(HttpStatus.NOT_FOUND, "NOT_FOUND", "Document or job unavailable."); }
  static FoliException failure(String code, String message) { return new FoliException(HttpStatus.CONFLICT, code, message); }
}
