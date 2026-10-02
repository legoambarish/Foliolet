package com.sih26190.dms.controller;

import java.util.Base64;
import java.nio.charset.StandardCharsets;

import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.sih26190.dms.dto.LoginRequest;
import com.sih26190.dms.dto.LoginResponse;
import com.sih26190.dms.dto.RegisterRequest;
import com.sih26190.dms.model.User;
import com.sih26190.dms.repository.UserRepository;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;


@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @PostMapping("/register")
    public ResponseEntity<String> register(@Valid @RequestBody RegisterRequest request) {
        if (request.getRole() == null || request.getRole() == com.sih26190.dms.model.Role.ADMIN) {
            return ResponseEntity.badRequest().body("Privileged roles cannot be self-registered");
        }
        if (!request.getUsername().matches("[a-zA-Z0-9_.-]{3,60}") || request.getPassword().length() < 12 || request.getPassword().getBytes(StandardCharsets.UTF_8).length > 72) {
            return ResponseEntity.badRequest().body("Use a 3-60 character username and a 12-72 character password");
        }
        if (userRepository.findByUsername(request.getUsername()).isPresent()) {
            return ResponseEntity.status(409).body("Username already exists");
        }

        User user = new User();
        user.setUsername(request.getUsername());
        user.setPassword(passwordEncoder.encode(request.getPassword()));
        user.setRole(request.getRole());

        try {
            // The database arbitrates concurrent registrations; the precheck is only UX.
            userRepository.saveAndFlush(user);
        } catch (org.springframework.dao.DataIntegrityViolationException conflict) {
            if (userRepository.findByUsername(request.getUsername()).isPresent()) {
                return ResponseEntity.status(409).body("Username already exists");
            }
            throw conflict;
        }

        return ResponseEntity.ok("User registered");
    }

    @PostMapping("/login")
    public ResponseEntity<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        return userRepository.findByUsername(request.getUsername())
                .filter(user -> passwordEncoder.matches(request.getPassword(), user.getPassword()))
                .map(user -> {
                    String credentials = request.getUsername() + ":" + request.getPassword();
                    String token = Base64.getEncoder().encodeToString(credentials.getBytes(StandardCharsets.UTF_8));
                    return ResponseEntity.ok(new LoginResponse(token, user.getRole().name(), user.getUsername()));
                })
                .orElseGet(() -> ResponseEntity.status(401).build());
    }

}
