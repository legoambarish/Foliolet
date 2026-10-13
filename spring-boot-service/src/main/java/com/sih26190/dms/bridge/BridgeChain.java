package com.sih26190.dms.bridge;

import jakarta.annotation.PostConstruct;
import java.math.*;
import java.nio.file.*;
import java.util.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Service;
import org.web3j.abi.*;
import org.web3j.abi.datatypes.*;
import org.web3j.abi.datatypes.generated.*;
import org.web3j.crypto.*;
import org.web3j.protocol.*;
import org.web3j.protocol.core.*;
import org.web3j.protocol.core.methods.request.Transaction;
import org.web3j.protocol.core.methods.response.*;
import org.web3j.tx.*;
import org.web3j.tx.response.*;

@Service
@ConditionalOnProperty(name = "bridge.enabled", havingValue = "true")
public class BridgeChain {
  public static final String ZERO = "0x" + "00".repeat(32);
  public final String registry, governance;
  public final long chainId;
  private final Web3j web3j;
  private final Environment env;
  private final Map<String, Credentials> signers = new HashMap<>();

  public BridgeChain(Web3j web3j, Environment env) {
    this.web3j = web3j;
    this.env = env;
    registry = env.getRequiredProperty("bridge.registry");
    governance = env.getRequiredProperty("bridge.governance");
    chainId = env.getProperty("blockchain.expected-chain-id", Long.class, 1337L);
  }

  @PostConstruct
  public void init() throws Exception {
    if (web3j.ethChainId().send().getChainId().longValue() != chainId)
      throw new IllegalStateException("Bridge chain mismatch");
    var actual =
        read(new Function("governance", List.of(), List.of(new TypeReference<Address>() {})), null)
            .get(0)
            .getValue();
    if (!BridgeProtocol.eq(actual, governance))
      throw new IllegalStateException("Governance pin mismatch");
    for (String actor :
        List.of(
            "governance",
            "university",
            "employer",
            "rogue",
            "internship-verifier",
            "tenant-verifier")) {
      String key = env.getProperty("bridge." + actor + "-key", "");
      if (!key.isBlank()) signers.put(actor, Credentials.create(key));
    }
    if (signers.containsKey("governance")
        && !BridgeProtocol.eq(signer("governance").getAddress(), governance))
      throw new IllegalStateException("Governance signing key mismatch");
  }

  public Credentials signer(String name) {
    var signer = signers.get(name);
    if (signer == null) throw new IllegalStateException("Named test signer unavailable");
    return signer;
  }

  public static Bytes32 b(String hex) {
    return new Bytes32(com.sih26190.dms.selective.MerkleTreeService.hex32(hex));
  }

  public synchronized TransactionReceipt send(String actor, String name, List<Type> args)
      throws Exception {
    var manager = new RawTransactionManager(web3j, signer(actor), chainId);
    var tx =
        manager.sendTransaction(
            BigInteger.valueOf(2000000000),
            BigInteger.valueOf(3000000),
            registry,
            FunctionEncoder.encode(new Function(name, args, List.of())),
            BigInteger.ZERO);
    if (tx.hasError())
      throw new IllegalArgumentException("Registry refused action: " + tx.getError().getMessage());
    var receipt =
        new PollingTransactionReceiptProcessor(web3j, 250, 80)
            .waitForTransactionReceipt(tx.getTransactionHash());
    if (!receipt.isStatusOK()) throw new IllegalArgumentException("Registry refused action");
    return receipt;
  }

  private List<Type> read(Function f, Long block) throws Exception {
    var call =
        web3j
            .ethCall(
                Transaction.createEthCallTransaction(
                    governance, registry, FunctionEncoder.encode(f)),
                block == null
                    ? DefaultBlockParameterName.LATEST
                    : DefaultBlockParameter.valueOf(BigInteger.valueOf(block)))
            .send();
    if (call.hasError() || call.isReverted())
      throw new IllegalStateException("Registry unavailable");
    return FunctionReturnDecoder.decode(call.getValue(), f.getOutputParameters());
  }

  public EthBlock.Block block() throws Exception {
    var block =
        web3j.ethGetBlockByNumber(DefaultBlockParameterName.LATEST, false).send().getBlock();
    if (block == null) throw new IllegalStateException("Chain unavailable");
    return block;
  }

  public Map<String, Object> evidence(String id, long block) throws Exception {
    var f = new Function("getEvidence", List.of(b(id)), List.of());
    var call =
        web3j
            .ethCall(
                Transaction.createEthCallTransaction(
                    governance, registry, FunctionEncoder.encode(f)),
                DefaultBlockParameter.valueOf(BigInteger.valueOf(block)))
            .send();
    String value = call.getValue();
    if (call.hasError() || value == null || value.length() != 2 + 14 * 64)
      throw new IllegalStateException("Invalid chain response");
    String[] words = new String[14];
    for (int i = 0; i < 14; i++) words[i] = value.substring(2 + i * 64, 2 + (i + 1) * 64);
    String[] names = {
      "root",
      "documentCommitment",
      "claimTypeHash",
      "issuer",
      "holder",
      "leafCount",
      "version",
      "issuedAt",
      "expiresAt",
      "anchorBlock",
      "changedBlock",
      "evidenceClass",
      "status",
      "supersededBy"
    };
    var result = new LinkedHashMap<String, Object>();
    for (int i = 0; i < names.length; i++)
      result.put(
          names[i],
          i < 3 || i == 13
              ? "0x" + words[i]
              : i == 3 || i == 4
                  ? "0x" + words[i].substring(24)
                  : new BigInteger(words[i], 16).longValueExact());
    return result;
  }

  public Map<String, Object> issuer(String address, String type, long block) throws Exception {
    var r =
        read(
            new Function(
                "issuers",
                List.of(new Address(address)),
                List.of(
                    new TypeReference<Utf8String>() {},
                    new TypeReference<Bool>() {},
                    new TypeReference<Bool>() {},
                    new TypeReference<Uint64>() {})),
            block);
    var scope =
        read(
            new Function(
                "scopes",
                List.of(new Address(address), b(Hash.sha3String(type))),
                List.of(new TypeReference<Bool>() {})),
            block);
    return Map.of(
        "name",
        r.get(0).getValue(),
        "recognized",
        r.get(1).getValue(),
        "suspended",
        r.get(2).getValue(),
        "changedBlock",
        ((BigInteger) r.get(3).getValue()).longValue(),
        "scoped",
        scope.get(0).getValue());
  }
}
