package com.sih26190.dms.intake;

import com.sih26190.dms.foli.*;
import com.sih26190.dms.model.*;
import com.sih26190.dms.repository.UserRepository;
import com.sih26190.dms.selective.*;
import com.sih26190.dms.selective.WalletDtos.*;
import com.sih26190.dms.selective.repository.IntegrityAgentRepository;
import java.nio.file.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.*;
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

/** Real database, AES vault, owner checks, canonical commitments and HTTP security.
 * Parser/model stand-ins here are complemented by the separately run live gate. */
class IntakeWorkflowTest extends WalletTestContext {
  static final Path ROOT=Path.of("target/intake-tests").toAbsolutePath().normalize();
  static final String FOLDER=ROOT.resolve("incoming").toString();
  static final byte[] CONTENT="Math: 90\nScience: 80\n".getBytes();
  static final String PROPOSAL="{\"fields\":[{\"page\":1,\"evidence\":\"Math: 90\",\"label\":\"Math\",\"type\":\"decimal\",\"value\":\"90\"},{\"page\":1,\"evidence\":\"Science: 80\",\"label\":\"Science\",\"type\":\"decimal\",\"value\":\"80\"}]}";
  @DynamicPropertySource static void isolated(DynamicPropertyRegistry p) {
    p.add("spring.datasource.url",() -> "jdbc:h2:mem:intake-tests;DB_CLOSE_DELAY=-1");
    p.add("wallet.data-dir",() -> ROOT.resolve("vault").toString());
    p.add("foli.temp-dir",() -> ROOT.resolve("tmp").toString());
  }
  @MockitoBean FoliReader reader;
  @MockitoBean FoliLocalModel model;
  @org.springframework.test.context.bean.override.mockito.MockitoSpyBean com.sih26190.dms.service.TextExtractionService legacyExtractor;
  @Autowired IntakeSessions sessions;
  @Autowired IntakeSessionRepository sessionRows;
  @Autowired IntakeJobs jobs;
  @Autowired IntakeMetadata metadata;
  @Autowired IntakeRecordRepository records;
  @Autowired IntegrityService integrity;
  @Autowired IntegrityAgentRepository agents;
  @Autowired WalletService wallet;
  @Autowired DisclosureService disclosure;
  @Autowired PresentationSigner signer;
  @Autowired AuthorizedDocumentResolver resolver;
  @Autowired FoliExtractionService extraction;
  @Autowired FoliWorkGate gate;
  @Autowired UserRepository users;
  @Autowired PasswordEncoder passwords;
  @Autowired WebApplicationContext context;
  User owner,other; MockMvc mvc;
  final String password="intake-isolated-password-42";
  User user() {var u=new User();u.setUsername("intake-test-"+UUID.randomUUID());u.setPassword(passwords.encode(password));u.setRole(Role.HOLDER);return users.saveAndFlush(u);}
  @BeforeEach void setup() {
    owner=user();other=user();mvc=MockMvcBuilders.webAppContextSetup(context).apply(springSecurity()).build();
    when(reader.inspect(any(),any())).thenAnswer(call -> {
      FoliData.Source source=call.getArgument(0);var snapshot=extraction.extract(source,s -> {});
      var indicators=new IntakeIndicators.Report("test",source.hash(),"NO_DIGILOCKER_INDICATOR",1,1,List.of(),List.of());
      return new FoliReader.Response(snapshot,null,null,null,200,indicators);
    });
    when(model.ask(anyString(),anyString(),eq(true))).thenReturn(new FoliLocalModel.Reply(PROPOSAL,1,10));
  }
  MockMultipartFile file(byte[] content) {return new MockMultipartFile("file","marks.txt","text/plain",content);}
  String draft() {return wallet.enroll(file(CONTENT),"Synthetic marks","Other",null,null,owner).get("id").toString();}
  Map<String,Object> done(String id) throws Exception {
    long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(8);
    Map<String,Object> result;
    do {result=jobs.get(id,owner);if(!Set.of("QUEUED","RUNNING").contains(result.get("state")))return result;Thread.sleep(25);}while(System.nanoTime()<deadline);
    fail("Bounded mock analysis did not finish");return result;
  }
  String observation(Map<String,Object> config,byte[] content,String filename) {
    var agent=agents.findById(config.get("agentId").toString()).orElseThrow();
    var input=new ObservationInput(agent.id,UUID.randomUUID().toString(),filename,PrivateVault.sha256(content),Instant.now().truncatedTo(java.time.temporal.ChronoUnit.SECONDS),agent.sequence+1,agent.lastDigest,"00".repeat(32));
    var sig=IntegrityService.hmac(MerkleTreeService.hex32(config.get("secret").toString()),IntegrityService.message(input));
    return integrity.observe(new ObservationInput(input.agentId(),input.itemId(),input.filename(),input.sha256(),input.observedAt(),input.sequence(),input.previousDigest(),sig)).get("observationId").toString();
  }
  @Test void pdfEnrollmentNeverInvokesTheUnboundedLegacyStripper() throws Exception {
    byte[] bytes="%PDF-1.7\nmalformed synthetic input\n%%EOF".getBytes();
    String id=wallet.enroll(new MockMultipartFile("file","untrusted.pdf","application/pdf",bytes),"Synthetic PDF","Other",null,null,owner).get("id").toString();
    assertArrayEquals(bytes,resolver.open("wallet:"+id,owner).bytes());
    assertTrue(((List<?>)wallet.detail(id,owner).get("suggestions")).isEmpty());
    verify(legacyExtractor,never()).extractBytes(any(),eq("untrusted.pdf"));
  }
  @Test void scopedSessionsRearmStopExpiryAndOwnerIsolation() {
    assertThrows(IllegalArgumentException.class,() -> sessions.arm(owner,"C:\\Users\\User\\Downloads"));
    var first=sessions.arm(owner,FOLDER);var second=sessions.arm(owner,FOLDER);
    assertThrows(RuntimeException.class,() -> sessions.authenticate(first.get("token").toString()));
    assertFalse(agents.findById(first.get("agentId").toString()).orElseThrow().active);
    assertTrue(sessions.list(other).isEmpty());
    assertThrows(RuntimeException.class,() -> sessions.stop(second.get("sessionId").toString(),other));
    sessions.stop(second.get("sessionId").toString(),owner);
    assertThrows(RuntimeException.class,() -> sessions.authenticate(second.get("token").toString()));
    var third=sessions.arm(owner,FOLDER);var row=sessionRows.findById(third.get("sessionId").toString()).orElseThrow();row.expiresAt=Instant.now().minusSeconds(1);sessionRows.saveAndFlush(row);
    assertThrows(RuntimeException.class,() -> sessions.authenticate(third.get("token").toString()));
    sessions.expire();assertFalse(agents.findById(third.get("agentId").toString()).orElseThrow().active);
  }
  @Test void appLifetimeHasNoTimerOrTenFileLimitButStopStillRevokes() {
    var config=sessions.arm(owner,FOLDER);
    assertEquals("app",config.get("lifetime")); assertNull(config.get("expiresAt")); assertEquals(0,config.get("maxFiles"));
    String id=config.get("sessionId").toString(),token=config.get("token").toString();
    var row=sessionRows.findById(id).orElseThrow(); row.createdAt=Instant.now().minusSeconds(86400); sessionRows.saveAndFlush(row);
    sessions.expire(); assertEquals(id,sessions.authenticate(token).id);
    assertNull(sessions.heartbeat(id,config.get("folderHash").toString()).get("expiresAt"));
    assertEquals(true,sessions.list(owner).get(0).get("connected"));
    for(int i=0;i<11;i++) {
      byte[] content=("Synthetic document "+i).getBytes(); String observed=observation(config,content,"marks.txt");
      sessions.upload(id,config.get("folderHash").toString(),"marks.txt",PrivateVault.sha256(content),observed,file(content));
    }
    assertEquals(11,sessionRows.findById(id).orElseThrow().imported);
    sessions.stop(id,owner); assertThrows(RuntimeException.class,() -> sessions.authenticate(token));
  }
  @Test void exactHashObservationUploadAndVaultAreBoundAndIdempotent() {
    var config=sessions.arm(owner,FOLDER);String sid=config.get("sessionId").toString(),folder=config.get("folderHash").toString(),hash=PrivateVault.sha256(CONTENT);
    String observed=observation(config,CONTENT,"marks.txt");
    assertThrows(RuntimeException.class,() -> sessions.upload(sid,folder,"marks.txt",hash,observed,file("Math: 95".getBytes())));
    var imported=sessions.upload(sid,folder,"marks.txt",hash,observed,file(CONTENT));
    var duplicate=sessions.upload(sid,folder,"marks.txt",hash,observed,file(CONTENT));
    assertEquals(imported.get("id"),duplicate.get("id"));assertEquals(true,duplicate.get("duplicate"));
    assertEquals(1,sessionRows.findById(sid).orElseThrow().imported);
    assertEquals(hash,resolver.open("wallet:"+imported.get("id"),owner).hash());
    assertEquals("FIRST_SEEN_TRACKED",wallet.detail(imported.get("id").toString(),owner).get("provenanceLevel"));
    assertEquals("WATCHER_ASSISTED",metadata.summary(imported.get("id").toString()).get("method"));
    for(String relative:List.of("../marks.txt","a/../../marks.txt","/marks.txt","a\\marks.txt",".hidden/marks.txt","marks.txt:stream"))
      assertThrows(RuntimeException.class,() -> sessions.upload(sid,folder,relative,hash,observed,file(CONTENT)),relative);
    assertThrows(RuntimeException.class,() -> sessions.upload(sid,"wrong", "marks.txt",hash,observed,file(CONTENT)));
    assertThrows(RuntimeException.class,() -> sessions.upload(sid,folder,"marks.txt",PrivateVault.sha256("different".getBytes()),observed,file("different".getBytes())));
  }
  @Test void anotherOwnersObservationCannotBeAttached() {
    var foreign=sessions.arm(other,FOLDER);String observed=observation(foreign,CONTENT,"marks.txt");
    var own=sessions.arm(owner,FOLDER);
    assertThrows(RuntimeException.class,() -> sessions.upload(own.get("sessionId").toString(),own.get("folderHash").toString(),"marks.txt",PrivateVault.sha256(CONTENT),observed,file(CONTENT)));
  }
  @Test void selectedFilesStayOwnerSessionAndByteBoundWithoutHistoricalObservation() {
    var previous=sessions.arm(owner,FOLDER); observation(previous,CONTENT,"marks.txt");
    var current=sessions.arm(owner,FOLDER); String sid=current.get("sessionId").toString(),folder=current.get("folderHash").toString();
    assertThrows(RuntimeException.class,() -> sessions.importSelected(sid,folder,"marks.txt",file(CONTENT),other));
    assertThrows(RuntimeException.class,() -> sessions.importSelected(previous.get("sessionId").toString(),folder,"marks.txt",file(CONTENT),owner));
    var first=sessions.importSelected(sid,folder,"marks.txt",file(CONTENT),owner);
    assertNull(sessionRows.findById(sid).orElseThrow().lastSeen,"Selecting a file does not imply a connected companion");
    assertEquals("SELF_ENROLLED",wallet.detail(first.get("id").toString(),owner).get("provenanceLevel"));
    assertArrayEquals(CONTENT,resolver.open("wallet:"+first.get("id"),owner).bytes());
    var duplicate=sessions.importSelected(sid,folder,"marks.txt",file(CONTENT),owner);
    assertEquals(first.get("id"),duplicate.get("id")); assertEquals(true,duplicate.get("duplicate"));
    byte[] changed="A different current document".getBytes();
    var second=sessions.importSelected(sid,folder,"marks.txt",file(changed),owner);
    assertNotEquals(first.get("id"),second.get("id")); assertArrayEquals(changed,resolver.open("wallet:"+second.get("id"),owner).bytes());
    sessions.stop(sid,owner);
    assertThrows(RuntimeException.class,() -> sessions.importSelected(sid,folder,"marks.txt",file(CONTENT),owner));
  }
  @Test void selectedImportReusesTheCurrentWatchersExactReceipt() {
    var current=sessions.arm(owner,FOLDER); String sid=current.get("sessionId").toString(),folder=current.get("folderHash").toString();
    String observed=observation(current,CONTENT,"marks.txt");
    var received=sessions.upload(sid,folder,"marks.txt",PrivateVault.sha256(CONTENT),observed,file(CONTENT));
    var selected=sessions.importSelected(sid,folder,"marks.txt",file(CONTENT),owner);
    assertEquals(received.get("id"),selected.get("id")); assertEquals(true,selected.get("duplicate"));
    assertEquals(1,sessionRows.findById(sid).orElseThrow().imported);
  }
  @Test void automaticReadingNeverRestartsCompletedJobsAndBaselineSurvivesRetry() throws Exception {
    String id=draft();jobs.automatically(id,owner);var result=done(id);assertEquals("READY",result.get("state"));
    String initial=records.findById(id).orElseThrow().encryptedBaseline;
    jobs.automatically(id,owner);assertEquals(1,metadata.detail(wallet.owned(id,owner)).get("attempts"));
    verify(reader,times(1)).inspect(any(),any());
    jobs.start(id,owner,true);done(id);assertEquals(initial,records.findById(id).orElseThrow().encryptedBaseline);
    assertNotNull(records.findById(id).orElseThrow().encryptedHistory);
    assertThrows(RuntimeException.class,() -> jobs.get(id,other));
    var fields=metadata.baseline(records.findById(id).orElseThrow()).fields().stream().map(FactSuggestions.Candidate::claim).toList();
    var changed=new ArrayList<>(fields);changed.set(0,new ClaimInput("education.math","Math","decimal","95"));
    wallet.confirm(id,new ConfirmClaims(changed),owner);
    assertEquals("SUGGESTIONS_MODIFIED",metadata.summary(id).get("lineage"));
    assertEquals(initial,records.findById(id).orElseThrow().encryptedBaseline);
    assertEquals("NOT_VERIFIED",metadata.summary(id).get("issuer"));
  }
  @Test void canonicalReorderEditsAdditionsRemovalsAndTypesAreCompared() throws Exception {
    String id=draft();jobs.automatically(id,owner);done(id);var baseline=metadata.baseline(records.findById(id).orElseThrow());
    assertEquals(FoliExtractionService.VERSION,baseline.extractor());assertNotNull(baseline.ocrEngine());
    var fields=new ArrayList<>(baseline.fields().stream().map(FactSuggestions.Candidate::claim).toList());Collections.reverse(fields);
    fields.set(1,new ClaimInput("education.math"," Math ","decimal","090.00"));
    assertEquals(new IntakeMetadata.Changes(0,0,0),metadata.compare(baseline,fields));
    wallet.confirm(id,new ConfirmClaims(fields),owner);assertEquals("SUGGESTIONS_UNMODIFIED",metadata.summary(id).get("lineage"));
    fields.add(new ClaimInput("extracted.extra","Extra","string","Holder text"));assertEquals(1,metadata.compare(baseline,fields).added());fields.remove(2);
    fields.remove(0);assertEquals(1,metadata.compare(baseline,fields).removed());
    fields.set(0,new ClaimInput("education.math","Math","string","90"));assertEquals(1,metadata.compare(baseline,fields).edited());
    fields.set(0,new ClaimInput("education.math_new","Math","decimal","90"));assertEquals(new IntakeMetadata.Changes(0,1,2),metadata.compare(baseline,fields));
    fields.add(fields.get(0));assertThrows(IllegalArgumentException.class,() -> metadata.compare(baseline,fields));
  }
  @Test void selectedLineageIsSignedScopedAndSurvivesReloadWithoutHiddenHistory() throws Exception {
    var anchors=new HashMap<String,com.sih26190.dms.blockchain.SelectiveDisclosureBlockchainService.ChainAnchor>();
    when(chain.address()).thenReturn("0x"+"11".repeat(20));when(chain.chainId()).thenReturn(1337L);when(chain.operator()).thenReturn(TEST_CREDENTIALS.getAddress());
    when(chain.get(anyString())).thenAnswer(call -> anchors.get(call.getArgument(0)));
    when(chain.anchor(anyString(),anyString(),anyString(),anyString(),anyInt(),anyInt(),nullable(String.class))).thenAnswer(call -> {
      anchors.put(call.getArgument(0),new com.sih26190.dms.blockchain.SelectiveDisclosureBlockchainService.ChainAnchor(call.getArgument(1),call.getArgument(2),call.getArgument(3),chain.operator(),Instant.now().truncatedTo(java.time.temporal.ChronoUnit.SECONDS),call.getArgument(4),call.getArgument(5),1,"0x"+"00".repeat(32)));
      return "0x"+"99".repeat(32);
    });
    String id=draft();jobs.automatically(id,owner);done(id);
    var b=metadata.baseline(records.findById(id).orElseThrow());var fields=new ArrayList<>(b.fields().stream().map(FactSuggestions.Candidate::claim).toList());
    fields.set(0,new ClaimInput("education.math","Math","decimal","95"));wallet.confirm(id,new ConfirmClaims(fields),owner);
    wallet.anchor(id,owner);
    var claim=wallet.claimRecords(id).stream().filter(c -> c.path.equals("education.math")).findFirst().orElseThrow();
    var share=disclosure.create(new ShareRequest(id,List.of(claim.id),"Test desk","Fictional demonstration",30,false,true),owner);
    String token=share.get("shareUrl").toString().split("/verify/")[1].replace("/","");
    var result=disclosure.open(token);assertTrue(result.verification().verified());var proof=result.bundle();
    assertEquals(1,proof.intakeStatus().facts().size());assertEquals("EDITED",proof.intakeStatus().facts().get(0).lineage());
    assertEquals("UNVERIFIED",proof.intakeStatus().issuer());assertFalse(proof.intakeStatus().toString().contains("Science"));
    assertFalse(proof.intakeStatus().toString().contains("90"));
    var s=proof.intakeStatus();var forged=new IntakeStatus(s.schema(),"PASSED",s.branding(),s.imported(),s.pdfSignature(),s.issuer(),s.facts());
    var altered=new Bundle(proof.format(),proof.credentialId(),proof.credentialVersion(),proof.merkleRoot(),proof.leafCount(),proof.anchor(),proof.provenance(),proof.presentation(),proof.claims(),proof.envelopeHash(),proof.platformSignature(),forged);
    assertFalse(signer.verify(altered));assertFalse(disclosure.verify(altered,true).verified());
    var stripped=new Bundle(proof.format(),proof.credentialId(),proof.credentialVersion(),proof.merkleRoot(),proof.leafCount(),proof.anchor(),proof.provenance(),proof.presentation(),proof.claims(),proof.envelopeHash(),proof.platformSignature());
    assertFalse(signer.verify(stripped));
    var privateStatus=metadata.disclosure(wallet.owned(id,owner),proof.claims(),resolver.open("wallet:"+id,owner).hash(),false);
    assertEquals("NOT_DISCLOSED",privateStatus.qr());assertEquals("NOT_DISCLOSED",privateStatus.imported());
    assertEquals("EDITED",privateStatus.facts().get(0).lineage());
    assertEquals("EDITED",disclosure.open(token).bundle().intakeStatus().facts().get(0).lineage());
  }
  @Test void manualConfirmationDuringReadingCannotAcquireALateBaseline() throws Exception {
    var entered=new CountDownLatch(1);var release=new CountDownLatch(1);
    doAnswer(call -> {entered.countDown();assertTrue(release.await(5,TimeUnit.SECONDS));FoliData.Source source=call.getArgument(0);return new FoliReader.Response(extraction.extract(source,x -> {}),null,null,null,200,new IntakeIndicators.Report("test",source.hash(),"NO_DIGILOCKER_INDICATOR",1,1,List.of(),List.of()));}).when(reader).inspect(any(),any());
    String id=draft();jobs.automatically(id,owner);assertTrue(entered.await(4,TimeUnit.SECONDS));
    try {wallet.confirm(id,new ConfirmClaims(List.of(new ClaimInput("education.math","Math","decimal","95"))),owner);}finally{release.countDown();}
    done(id);assertNull(records.findById(id).orElseThrow().encryptedBaseline);assertEquals("NOT_ASSESSED",metadata.summary(id).get("lineage"));
  }
  @Test void modelOutageKeepsOriginalAndAllowsManualConfirmation() throws Exception {
    when(model.ask(anyString(),anyString(),eq(true))).thenThrow(new FoliException(org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE,"OFFLINE","Local model offline"));
    String id=draft();jobs.automatically(id,owner);assertEquals("READY",done(id).get("state"));verify(model,never()).ask(anyString(),anyString(),anyBoolean());
    assertArrayEquals(CONTENT,resolver.open("wallet:"+id,owner).bytes());
    wallet.confirm(id,new ConfirmClaims(List.of(new ClaimInput("education.math","Math","decimal","90"))),owner);
    assertEquals("SUGGESTIONS_MODIFIED",metadata.summary(id).get("lineage"));
  }
  @Test void aBriefFoliSourceReadDoesNotDropAutomaticAnalysis() throws Exception {
    var held=new CountDownLatch(1);var release=new CountDownLatch(1);
    var executor=Executors.newSingleThreadExecutor();
    var reading=executor.submit(() -> gate.reading(() -> {held.countDown();try {release.await(4,TimeUnit.SECONDS);}catch(InterruptedException e){Thread.currentThread().interrupt();}return true;}));
    try {
      assertTrue(held.await(2,TimeUnit.SECONDS));String id=draft();jobs.automatically(id,owner);
      Thread.sleep(100);assertTrue(Set.of("RUNNING","QUEUED").contains(jobs.get(id,owner).get("state")));
      release.countDown();reading.get(2,TimeUnit.SECONDS);assertEquals("READY",done(id).get("state"));
    } finally {release.countDown();executor.shutdownNow();}
  }
  @Test void capabilityHasNoWalletAuthorityNoBrowserOriginAndNoRemoteUse() throws Exception {
    var config=sessions.arm(owner,FOLDER);String bearer="Bearer "+config.get("token"),folder=config.get("folderHash").toString();
    mvc.perform(post("/api/intake-agent/heartbeat").header("Authorization",bearer).param("folderHash",folder)).andExpect(status().isOk());
    mvc.perform(post("/api/intake-agent/heartbeat").header("Authorization",bearer).header("Origin","http://evil.example").param("folderHash",folder)).andExpect(status().isUnauthorized());
    mvc.perform(post("/api/intake-agent/heartbeat").with(request -> {request.setRemoteAddr("192.0.2.1");return request;}).header("Authorization",bearer).param("folderHash",folder)).andExpect(status().isUnauthorized());
    mvc.perform(post("/api/intake-agent/heartbeat").with(httpBasic(owner.getUsername(),password)).param("folderHash",folder)).andExpect(status().isUnauthorized());
    mvc.perform(get("/api/wallet/documents").header("Authorization",bearer)).andExpect(status().isUnauthorized());
    mvc.perform(get("/api/wallet/intake/sessions").with(httpBasic(other.getUsername(),password))).andExpect(status().isOk()).andExpect(content().json("[]"));
    sessions.stop(config.get("sessionId").toString(),owner);
    mvc.perform(post("/api/intake-agent/heartbeat").header("Authorization",bearer).param("folderHash",folder)).andExpect(status().isUnauthorized());
  }
}
