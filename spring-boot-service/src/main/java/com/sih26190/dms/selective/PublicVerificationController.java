package com.sih26190.dms.selective;

import com.sih26190.dms.selective.WalletDtos.*;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

@RestController
public class PublicVerificationController {
  private final DisclosureService disclosures;
  private final IntegrityService integrity;
  private final WalletJson json;
  private final com.sih26190.dms.blockchain.SelectiveDisclosureBlockchainService chain;

  public PublicVerificationController(
      DisclosureService disclosures,
      IntegrityService integrity,
      WalletJson json,
      com.sih26190.dms.blockchain.SelectiveDisclosureBlockchainService chain) {
    this.disclosures = disclosures;
    this.integrity = integrity;
    this.json = json;
    this.chain = chain;
  }

  @GetMapping("/api/public/network")
  public Object network() {
    return java.util.Map.of(
        "contract", chain.address(), "chainId", chain.chainId(), "operator", chain.operator());
  }

  // GET does not release information or consume a one-time grant. Link scanners see the landing UI
  // only.
  @PostMapping("/api/public/disclosures/{token}/open")
  public PublicResult open(@PathVariable String token) {
    return disclosures.open(token);
  }

  @PostMapping("/api/public/verify-bundle")
  public CheckResult verify(@RequestBody String bundle) {
    return disclosures.verify(json.readBundle(bundle), true);
  }

  @GetMapping("/api/public/grants/{id}/status")
  public Object status(@PathVariable String id) {
    return disclosures.status(id);
  }

  @PostMapping("/api/integrity/observations")
  public Object observe(@Valid @RequestBody ObservationInput input) {
    return integrity.observe(input);
  }
}
