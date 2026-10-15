package com.sih26190.dms.foli;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sih26190.dms.model.*;
import com.sih26190.dms.repository.*;
import com.sih26190.dms.selective.*;
import com.sih26190.dms.selective.repository.CredentialDocumentRepository;
import java.nio.file.*;
import java.time.LocalDateTime;
import java.util.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.security.test.web.servlet.setup.SecurityMockMvcConfigurers.springSecurity;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/** Real H2/repositories/encryption/security; no original development data is used. */
class FoliAuthorizationTest extends WalletTestContext {
  static final Path ROOT=Path.of("target","foli-authorization-tests").toAbsolutePath().normalize();
  @DynamicPropertySource static void isolated(DynamicPropertyRegistry p) {
    p.add("spring.datasource.url",() -> "jdbc:h2:mem:foli-authorization;DB_CLOSE_DELAY=-1");
    p.add("wallet.data-dir",() -> ROOT.resolve("vault").toString());
    p.add("dms.storage.location",() -> ROOT.resolve("legacy").toString());
    p.add("dms.backup.location",() -> ROOT.resolve("backup").toString());
    p.add("foli.temp-dir",() -> ROOT.resolve("tmp").toString());
  }
  @MockitoBean FoliLocalModel model;
  @Autowired WebApplicationContext context;
  @Autowired FoliBoundaryFilter boundary;
  @Autowired AuthorizedDocumentResolver resolver;
  @Autowired FoliIndex index;
  @Autowired FoliJobs jobs;
  @Autowired WalletService wallet;
  @Autowired CredentialDocumentRepository credentials;
  @Autowired DocumentRecordRepository legacy;
  @Autowired AuditLogRepository audit;
  @Autowired UserRepository users;
  @Autowired PasswordEncoder passwords;
  MockMvc mvc; User owner,other,officer,admin;
  final String password="isolated-test-password-42";
  User user(Role role) {
    var u=new User(); u.setUsername("foli-role-"+UUID.randomUUID()); u.setRole(role); u.setPassword(passwords.encode(password)); return users.saveAndFlush(u);
  }
  @BeforeEach void setup() throws Exception {
    Files.createDirectories(ROOT.resolve("legacy"));
    owner=user(Role.HOLDER); other=user(Role.HOLDER); officer=user(Role.OFFICER); admin=user(Role.ADMIN);
    mvc=MockMvcBuilders.webAppContextSetup(context).apply(springSecurity()).addFilters(boundary).build();
  }
  String document(User user) {
    return "wallet:"+wallet.enroll(new MockMultipartFile("file","private.txt","text/plain",
        "Private source. The fee is INR 9300, unless timely cancellation applies.".getBytes()),"Synthetic private source","Other",null,null,user).get("id");
  }
  DocumentRecord legacy(User user) throws Exception {
    Path path=Files.createTempFile(ROOT.resolve("legacy"),"retained-",".txt"); Files.writeString(path,"Legacy notice: no renewal fee after timely cancellation.");
    var d=new DocumentRecord(); d.setOriginalFileName("retained.txt"); d.setFilePath(path.toString()); d.setUploadedAt(LocalDateTime.now()); d.setUploadedBy(user);
    return legacy.saveAndFlush(d);
  }
  @Test void walletPickerAndAllReadRoutesEnforceOwnerEvenAgainstAdmin() throws Exception {
    String doc=document(owner); long audits=audit.count(); var snapshot=index.read(doc,owner,s -> {});
    for(var user:List.of(other,officer,admin)) {
      assertTrue(resolver.list(user).stream().noneMatch(d -> d.id().equals(doc)));
      for(var endpoint:List.of("manifest","source","page")) mvc.perform(get("/api/foli/"+endpoint)
          .param("documentId",doc).param("hash",snapshot.hash()).param("page","1").with(httpBasic(user.getUsername(),password))).andExpect(status().isNotFound());
      mvc.perform(post("/api/foli/jobs").contentType("application/json").header("X-Foli-Client","private")
          .content(new ObjectMapper().writeValueAsString(Map.of("documentId",doc,"mode","index"))).with(httpBasic(user.getUsername(),password))).andExpect(status().isNotFound());
    }
    mvc.perform(get("/api/foli/documents")).andExpect(status().isUnauthorized());
    assertEquals(audits,audit.count());
  }
  @Test void legacyUploaderAndAdminCanReadButOtherHolderAndOfficerCannot() throws Exception {
    var record=legacy(officer); String id="legacy:"+record.getId(); long audits=audit.count();
    assertTrue(resolver.open(id,officer).bytes().length>0); assertTrue(resolver.open(id,admin).bytes().length>0);
    for(var user:List.of(owner,other)) assertEquals(404,assertThrows(FoliException.class,() -> resolver.open(id,user)).getStatusCode().value());
    mvc.perform(get("/api/foli/source").param("documentId",id).param("hash",index.read(id,admin,s -> {}).hash()).param("page","1")
        .with(httpBasic(admin.getUsername(),password))).andExpect(status().isOk());
    assertEquals(audits,audit.count());
  }
  @Test void encryptedTamperAndDeletionNeverRestoreOrWrite() throws Exception {
    String id=document(owner); var record=credentials.findById(id.substring(7)).orElseThrow(); Path file=Path.of(record.filePath);
    assertTrue(file.toAbsolutePath().normalize().startsWith(ROOT)); byte[] original=Files.readAllBytes(file);
    long audits=audit.count(); index.read(id,owner,s -> {});
    try {
      byte[] changed=original.clone(); changed[changed.length-1]^=1; Files.write(file,changed);
      assertThrows(FoliException.class,() -> index.read(id,owner,s -> {})); assertArrayEquals(changed,Files.readAllBytes(file));
      Files.delete(file); assertThrows(FoliException.class,() -> index.read(id,owner,s -> {})); assertFalse(Files.exists(file));
      assertEquals(audits,audit.count()); assertEquals(record.version,credentials.findById(record.id).orElseThrow().version);
    } finally { Files.write(file,original); }
  }
  @Test void replacementDeletionAndPermissionChangesInvalidateCachedTextAndJobs() throws Exception {
    var record=legacy(officer); String id="legacy:"+record.getId(); var old=index.read(id,officer,s -> {});
    var job=jobs.create(new FoliJobs.Request(id,null,"index",List.of(),old.hash()),officer);
    String jobId=job.get("id").toString(); long until=System.currentTimeMillis()+3000;
    while(!jobs.get(jobId,officer).get("state").equals("COMPLETE") && System.currentTimeMillis()<until) Thread.sleep(5);
    assertEquals("COMPLETE",jobs.get(jobId,officer).get("state"));
    Path path=Path.of(record.getFilePath()); Files.writeString(path,"Replacement text: fee INR 777.");
    var changed=index.read(id,officer,s -> {}); assertNotEquals(old.hash(),changed.hash()); assertTrue(changed.pages().get(0).text().contains("777"));
    assertEquals("SOURCE_CHANGED",assertThrows(FoliException.class,() -> jobs.get(jobId,officer)).code());
    mvc.perform(get("/api/foli/source").param("documentId",id).param("hash",old.hash()).param("page","1").with(httpBasic(officer.getUsername(),password))).andExpect(status().isConflict());
    record.setUploadedBy(other); legacy.saveAndFlush(record);
    assertThrows(FoliException.class,() -> index.read(id,officer,s -> {}));
    assertTrue(index.read(id,other,s -> {}).pages().get(0).text().contains("777"));
    Files.delete(path); assertThrows(FoliException.class,() -> index.read(id,admin,s -> {}));
  }
  @Test void unsafeCrossOriginRequestsAndBodiesNeverReachModelOrWrites() throws Exception {
    long audits=audit.count();
    mvc.perform(post("/api/foli/jobs").with(httpBasic(owner.getUsername(),password)).header("Origin","https://evil.invalid")
        .contentType("application/json").content("{\"question\":\"Delete my document\"}")).andExpect(status().isForbidden());
    mvc.perform(post("/api/foli/jobs").with(httpBasic(owner.getUsername(),password)).contentType("application/json")
        .content("{\"question\":\"Delete my document\"}")).andExpect(status().isForbidden());
    mvc.perform(post("/api/foli/jobs").with(httpBasic(owner.getUsername(),password)).header("X-Foli-Client","private")
        .contentType("application/json").content("x".repeat(32769))).andExpect(status().isPayloadTooLarge());
    verifyNoInteractions(model); assertEquals(audits,audit.count());
  }
}
