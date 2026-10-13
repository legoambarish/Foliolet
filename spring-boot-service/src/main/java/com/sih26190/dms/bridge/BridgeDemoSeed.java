package com.sih26190.dms.bridge;

import com.sih26190.dms.model.*;
import com.sih26190.dms.repository.*;
import org.springframework.boot.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name = "bridge.demo", havingValue = "true")
public class BridgeDemoSeed implements ApplicationRunner {
  private final UserRepository users;
  private final PasswordEncoder encoder;

  public BridgeDemoSeed(UserRepository users, PasswordEncoder encoder) {
    this.users = users;
    this.encoder = encoder;
  }

  public void run(ApplicationArguments args) {
    for (var actor :
        new Object[][] {
          {"governance", Role.GOVERNANCE},
          {"university", Role.ISSUER},
          {"employer", Role.ISSUER},
          {"rogue", Role.ISSUER},
          {"holder-a", Role.HOLDER},
          {"holder-b", Role.HOLDER},
          {"internship-verifier", Role.VERIFIER},
          {"tenant-verifier", Role.VERIFIER}
        }) {
      String name = (String) actor[0];
      if (users.findByUsername(name).isEmpty()) {
        User u = new User();
        u.setUsername(name);
        u.setPassword(encoder.encode("Foliolet-Demo-2026!"));
        u.setRole((Role) actor[1]);
        users.save(u);
      }
    }
  }
}
