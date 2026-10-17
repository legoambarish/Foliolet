package com.sih26190.dms.service;

import com.sih26190.dms.model.*;
import com.sih26190.dms.repository.*;
import java.net.http.*;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.server.ResponseStatusException;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class ExternalAiPrivacyTest {
  private AiAnalysisService service(DocumentRecordRepository documents, TextExtractionService extractor, HttpClient http) {
    var service = new AiAnalysisService(documents, mock(AiInsightRepository.class), extractor, mock(AuditService.class));
    ReflectionTestUtils.setField(service,"httpClient",http);
    ReflectionTestUtils.setField(service,"openRouterApiKey","");
    ReflectionTestUtils.setField(service,"openRouterModel","fictional-model");
    return service;
  }

  /** This exact test also compiles against the old baseline: the HTTP client is mocked. */
  @Test void anEmptyApiKeyMustNeverCauseEvenAnUnauthorizedOutboundRequest() throws Exception {
    var documents=mock(DocumentRecordRepository.class);var extractor=mock(TextExtractionService.class);
    var http=mock(HttpClient.class);var service=service(documents,extractor,http);
    var owner=new User();owner.setId(1L);owner.setUsername("fictional-holder");owner.setRole(Role.HOLDER);
    var document=new DocumentRecord();document.setId(1L);document.setUploadedBy(owner);
    document.setFilePath("fictional.txt");document.setOriginalFileName("fictional.txt");
    when(documents.findById(1L)).thenReturn(Optional.of(document));
    when(extractor.extractText(any(),anyString())).thenReturn("Fictional private document body");
    HttpResponse<Object> denied=mock(HttpResponse.class);when(denied.statusCode()).thenReturn(401);
    when(http.send(any(HttpRequest.class),any(HttpResponse.BodyHandler.class))).thenReturn(denied);
    assertThrows(RuntimeException.class,()->service.analyze(1L,owner));
    verifyNoInteractions(http);
  }

  @Test void administratorSwitchAndRequestConsentAndKeyAreAllRequiredBeforeSourceAccess() {
    for(boolean enabled:new boolean[]{false,true})for(boolean consent:new boolean[]{false,true})for(String key:new String[]{"","fictional-key"}) {
      if(enabled&&consent&&!key.isEmpty())continue;
      var documents=mock(DocumentRecordRepository.class);var extractor=mock(TextExtractionService.class);var http=mock(HttpClient.class);
      var service=service(documents,extractor,http);
      ReflectionTestUtils.setField(service,"externalAiEnabled",enabled);ReflectionTestUtils.setField(service,"openRouterApiKey",key);
      var error=assertThrows(ResponseStatusException.class,()->service.analyze(1L,new User(),consent));
      assertEquals(403,error.getStatusCode().value());
      verifyNoInteractions(documents,extractor,http);
    }
  }

  @Test void aLegacyCallerCannotImplicitlyConsentEvenWithAnEnabledProvider() {
    var documents=mock(DocumentRecordRepository.class);var extractor=mock(TextExtractionService.class);var http=mock(HttpClient.class);
    var service=service(documents,extractor,http);
    ReflectionTestUtils.setField(service,"externalAiEnabled",true);ReflectionTestUtils.setField(service,"openRouterApiKey","fictional-key");
    assertThrows(ResponseStatusException.class,()->service.analyze(1L,new User()));
    verifyNoInteractions(documents,extractor,http);
  }
}
