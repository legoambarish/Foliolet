package com.sih26190.dms.selective;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import com.sih26190.dms.controller.AuthController;
import com.sih26190.dms.dto.RegisterRequest;
import com.sih26190.dms.model.*;
import com.sih26190.dms.repository.UserRepository;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.security.crypto.password.PasswordEncoder;

class UsernameUniquenessTest extends WalletTestContext {
  @Autowired UserRepository users;

  @Test void databaseRejectsDuplicateUsername() {
    String name = "unique-" + UUID.randomUUID();
    users.saveAndFlush(new User(null, name, "fixture", Role.HOLDER));
    assertThrows(DataIntegrityViolationException.class,
        () -> users.saveAndFlush(new User(null, name, "fixture", Role.HOLDER)));
    assertTrue(users.findByUsername(name).isPresent());
  }

  @Test void raceConflictIsControlled() {
    var repo = mock(UserRepository.class);
    var encoder = mock(PasswordEncoder.class);
    var request = new RegisterRequest();
    request.setUsername("race-holder");
    request.setPassword("local-password-123");
    request.setRole(Role.HOLDER);
    when(repo.findByUsername("race-holder"))
        .thenReturn(Optional.empty()).thenReturn(Optional.of(new User()));
    when(repo.saveAndFlush(any())).thenThrow(new DataIntegrityViolationException("duplicate"));
    var result = new AuthController(repo, encoder).register(request);
    assertEquals(409, result.getStatusCode().value());
    assertEquals("Username already exists", result.getBody());
  }
}
