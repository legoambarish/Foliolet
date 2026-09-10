package com.sih26190.dms.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.sih26190.dms.dto.AiAnalysisResponse;
import com.sih26190.dms.model.User;
import com.sih26190.dms.repository.UserRepository;
import com.sih26190.dms.service.AiAnalysisService;

import lombok.RequiredArgsConstructor;


@RestController
@RequestMapping("/api/documents")
@RequiredArgsConstructor
public class AiAnalysisController {

    private final AiAnalysisService aiAnalysisService;
    private final UserRepository userRepository;

    @PostMapping("/{id}/analyze")
    public AiAnalysisResponse analyze(@PathVariable Long id, Authentication authentication) {
        User requester = currentUser(authentication);
        return aiAnalysisService.analyze(id, requester);
    }

    @GetMapping("/{id}/analysis")
    public ResponseEntity<AiAnalysisResponse> getLatest(@PathVariable Long id, Authentication authentication) {
        User requester = currentUser(authentication);
        AiAnalysisResponse response = aiAnalysisService.getLatest(id, requester);
        return response == null ? ResponseEntity.noContent().build() : ResponseEntity.ok(response);
    }

    private User currentUser(Authentication authentication) {
        String username = authentication.getName();
        return userRepository.findByUsername(username)
                .orElseThrow(() -> new RuntimeException("Authenticated user not found: " + username));
    }

}