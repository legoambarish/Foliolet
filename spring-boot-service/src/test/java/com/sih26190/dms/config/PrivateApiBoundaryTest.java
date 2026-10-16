package com.sih26190.dms.config;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import java.util.concurrent.atomic.AtomicBoolean;
import static org.junit.jupiter.api.Assertions.*;

class PrivateApiBoundaryTest {
  private void check(String method, String path, String origin, String fetchSite, boolean allowed) throws Exception {
    var request = new MockHttpServletRequest(method,path);
    if(origin != null)request.addHeader("Origin",origin);
    if(fetchSite != null)request.addHeader("Sec-Fetch-Site",fetchSite);
    request.addHeader("Authorization","Basic ZmljdGlvbmFsOmZpeHR1cmU=");
    var response=new MockHttpServletResponse();var reached=new AtomicBoolean();
    new PrivateApiBoundaryFilter().doFilter(request,response,(req,res)->reached.set(true));
    assertEquals(allowed,reached.get());
    if(!allowed){assertEquals(403,response.getStatus());assertEquals("no-store",response.getHeader("Cache-Control"));}
  }
  @Test void browserOriginsCannotReachPrivateActionsWithCachedBasicCredentials() throws Exception {
    for(String origin:new String[]{"https://outside.invalid","null","http://localhost:8000"})
      for(String path:new String[]{"/api/wallet/documents/abc/anchor","/api/auth/register","/api/documents/1","/api/cases/1","/api/audit-log"})
        check("POST",path,origin,null,false);
  }
  @Test void_crossSiteMetadataCannotBypassMissingOrigin() throws Exception {
    check("POST","/api/wallet/disclosures/abc/revoke",null,"cross-site",false);
    check("GET","/api/wallet/documents",null,"same-site",false);
  }
  @Test void privateServerAndNativeClientsRemainCompatible() throws Exception {
    check("GET","/api/wallet/documents",null,null,true);
    check("POST","/api/auth/login",null,null,true);
  }
  @Test void publicIndependentVerificationIsOutsideThisPrivateBoundary() throws Exception {
    check("POST","/api/public/verify","http://localhost:8000","cross-site",true);
    check("GET","/api/public/network","http://localhost:8000",null,true);
  }
}
