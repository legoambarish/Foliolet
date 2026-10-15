package com.sih26190.dms.foli;

import jakarta.servlet.*;
import jakarta.servlet.http.*;
import java.io.*;
import java.util.Set;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/** Private loopback API, custom-header CSRF barrier, bounded bodies, no CORS. */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 20)
public class FoliBoundaryFilter extends OncePerRequestFilter {
  private final FoliProperties config;
  private final java.util.concurrent.Semaphore requests=new java.util.concurrent.Semaphore(4);
  public FoliBoundaryFilter(FoliProperties config) { this.config = config; }
  @Override protected boolean shouldNotFilter(HttpServletRequest request) {
    return !request.getRequestURI().startsWith("/api/foli");
  }
  @Override protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
      FilterChain chain) throws ServletException, IOException {
    response.setHeader("Cache-Control", "no-store, private");
    response.setHeader("Referrer-Policy", "no-referrer");
    response.setHeader("X-Content-Type-Options", "nosniff");
    if (!Set.of("127.0.0.1", "::1", "0:0:0:0:0:0:0:1").contains(request.getRemoteAddr())) {
      reject(response, 404, "NOT_FOUND", "Private service unavailable."); return;
    }
    if (!config.isEnabled()) { reject(response, 503, "DISABLED", "Foli is disabled."); return; }
    if (!Set.of("GET", "HEAD", "POST", "DELETE").contains(request.getMethod())) {
      reject(response, 405, "METHOD", "Unsupported method."); return;
    }
    if (request.getHeader("Origin") != null || (!Set.of("GET", "HEAD").contains(request.getMethod()) &&
        !"private".equals(request.getHeader("X-Foli-Client")))) {
      reject(response, 403, "CSRF", "Use the authenticated private application."); return;
    }
    if ("POST".equals(request.getMethod())) {
      if (request.getContentType() == null || !request.getContentType().startsWith("application/json")) {
        reject(response, 415, "CONTENT_TYPE", "Use a JSON request."); return;
      }
      byte[] body = request.getInputStream().readNBytes(32769);
      if (body.length > 32768) { reject(response, 413, "INPUT_LIMIT", "Request exceeds 32 KiB."); return; }
      request = new HttpServletRequestWrapper(request) {
        @Override public ServletInputStream getInputStream() {
          var input = new ByteArrayInputStream(body);
          return new ServletInputStream() {
            @Override public int read() { return input.read(); }
            @Override public int read(byte[] b, int off, int len) { return input.read(b,off,len); }
            @Override public boolean isFinished() { return input.available()==0; }
            @Override public boolean isReady() { return true; }
            @Override public void setReadListener(ReadListener listener) { throw new UnsupportedOperationException(); }
          };
        }
        @Override public BufferedReader getReader() { return new BufferedReader(new InputStreamReader(getInputStream(), java.nio.charset.StandardCharsets.UTF_8)); }
      };
    }
    if(!requests.tryAcquire()) { reject(response,429,"BUSY","The private reader is busy. Retry shortly."); return; }
    try { chain.doFilter(request,response); }
    finally { requests.release(); }
  }
  private static void reject(HttpServletResponse response, int status, String code, String message) throws IOException {
    response.setStatus(status); response.setContentType("application/json");
    response.getWriter().write("{\"code\":\""+code+"\",\"message\":\""+message+"\"}");
  }
}
