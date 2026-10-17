package com.sih26190.dms.intake;

import jakarta.servlet.*;
import jakarta.servlet.http.*;
import java.io.IOException;
import java.util.List;
import org.springframework.context.annotation.*;
import org.springframework.core.annotation.Order;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.www.BasicAuthenticationFilter;
import org.springframework.web.filter.OncePerRequestFilter;

/** This capability can authenticate only the two narrow companion endpoints. */
@Configuration
public class IntakeAgentSecurity {
  @Bean @Order(1)
  SecurityFilterChain intakeAgentChain(HttpSecurity http,IntakeSessions sessions) throws Exception {
    http.securityMatcher("/api/intake-agent/**").csrf(c -> c.disable())
        .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
        .authorizeHttpRequests(a -> a.anyRequest().hasRole("INTAKE"))
        .addFilterBefore(new OncePerRequestFilter() {
          @Override protected void doFilterInternal(HttpServletRequest req,HttpServletResponse res,FilterChain chain) throws ServletException,IOException {
            res.setHeader("Cache-Control","no-store");
            String header=req.getHeader("Authorization");
            if(!List.of("127.0.0.1","::1","0:0:0:0:0:0:0:1").contains(req.getRemoteAddr()) || req.getHeader("Origin")!=null
                || !"POST".equals(req.getMethod()) || header==null || !header.startsWith("Bearer ")) { res.sendError(401); return; }
            try {
              var s=sessions.authenticate(header.substring(7));
              var auth=new UsernamePasswordAuthenticationToken(s.id,null,List.of(new SimpleGrantedAuthority("ROLE_INTAKE")));
              SecurityContextHolder.getContext().setAuthentication(auth);
            } catch(RuntimeException e) { res.sendError(401); return; }
            chain.doFilter(req,res);
          }
        },BasicAuthenticationFilter.class);
    return http.build();
  }
}
