package com.sih26190.dms.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Set;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Private Spring APIs are reached through the CSRF-protected Django bridge or
 * explicit native clients, never directly from a web origin. HTTP Basic being
 * stateless does not by itself prevent browser credential replay/CSRF.
 * This does not replace loopback binding, authentication, or network isolation.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 10)
public class PrivateApiBoundaryFilter extends OncePerRequestFilter {
  @Override protected boolean shouldNotFilter(HttpServletRequest request) {
    String path = request.getRequestURI();
    return Set.of("/api/wallet", "/api/auth", "/api/documents", "/api/cases", "/api/audit-log")
        .stream().noneMatch(prefix -> path.equals(prefix) || path.startsWith(prefix + "/"));
  }

  @Override protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
      FilterChain chain) throws ServletException, IOException {
    String site = request.getHeader("Sec-Fetch-Site");
    if (request.getHeader("Origin") != null || "cross-site".equals(site) || "same-site".equals(site)) {
      response.setStatus(403);
      response.setContentType("application/json");
      response.setHeader("Cache-Control", "no-store");
      response.getWriter().write("{\"code\":\"PRIVATE_API_ORIGIN\",\"message\":\"Use the authenticated private application.\"}");
      return;
    }
    chain.doFilter(request, response);
  }
}
