package com.sih26190.dms.selective;

import com.sih26190.dms.blockchain.*;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

@SpringBootTest
@ActiveProfiles("test")
public abstract class WalletTestContext {
  protected static final org.web3j.crypto.Credentials TEST_CREDENTIALS = testCredentials();

  private static org.web3j.crypto.Credentials testCredentials() {
    try {
      return org.web3j.crypto.Credentials.create(org.web3j.crypto.Keys.createEcKeyPair());
    } catch (Exception e) {
      throw new IllegalStateException("Cannot initialize isolated test signer", e);
    }
  }

  @org.springframework.test.context.DynamicPropertySource
  static void testSigningKey(org.springframework.test.context.DynamicPropertyRegistry properties) {
    properties.add("blockchain.private-key",
        () -> TEST_CREDENTIALS.getEcKeyPair().getPrivateKey().toString(16));
  }

  // Network mocks are confined to this isolated database/service test context.
  @MockitoBean protected BlockchainService legacyChain;
  @MockitoBean protected EvmGateway gateway;
  @MockitoBean protected SelectiveDisclosureBlockchainService chain;
}
