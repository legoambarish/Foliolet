package com.sih26190.dms.selective;

import jakarta.servlet.*;
import jakarta.servlet.http.*;
import java.io.IOException;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
public class PrivateResponseFilter extends OncePerRequestFilter {
  @Override
  protected void doFilterInternal(
      HttpServletRequest request, HttpServletResponse response, FilterChain chain)
      throws ServletException, IOException {
    if (request.getRequestURI().startsWith("/api/wallet")
        || request.getRequestURI().startsWith("/api/public")) {
      response.setHeader("Cache-Control", "no-store");
      response.setHeader("Referrer-Policy", "no-referrer");
      response.setHeader("X-Content-Type-Options", "nosniff");
    }
    if (request.getRequestURI().startsWith("/api/public")
        && request.getContentLengthLong() > 256 * 1024) {
      response.sendError(413);
      return;
    }
    chain.doFilter(request, response);
  }
}
