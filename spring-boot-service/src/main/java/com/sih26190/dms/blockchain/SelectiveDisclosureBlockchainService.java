package com.sih26190.dms.blockchain;

import com.sih26190.dms.selective.MerkleTreeService;
import jakarta.annotation.PostConstruct;
import java.math.BigInteger;
import java.time.Instant;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.web3j.abi.*;
import org.web3j.abi.datatypes.*;
import org.web3j.abi.datatypes.generated.*;
import org.web3j.protocol.Web3j;
import org.web3j.protocol.core.DefaultBlockParameterName;
import org.web3j.protocol.core.methods.request.Transaction;
import org.web3j.utils.Numeric;

@Service
public class SelectiveDisclosureBlockchainService {
  public static final String ZERO = "0x" + "00".repeat(32);
  private final EvmGateway gateway;
  private final Web3j web3j;
  private String address;

  public record ChainAnchor(
      String root,
      String documentCommitment,
      String provenanceDigest,
      String owner,
      Instant anchoredAt,
      int version,
      int provenanceLevel,
      int status,
      String supersededBy) {}

  public SelectiveDisclosureBlockchainService(
      EvmGateway gateway,
      Web3j web3j,
      @Value("${blockchain.selective-contract-address:}") String configured) {
    this.gateway = gateway;
    this.web3j = web3j;
    address = configured;
  }

  @PostConstruct
  public void init() throws Exception {
    address = gateway.deployment("SelectiveDisclosureRegistry", address);
    var function = new Function("operator", List.of(), List.of(new TypeReference<Address>() {}));
    if (!read(function).get(0).getValue().toString().equalsIgnoreCase(operator()))
      throw new IllegalStateException(
          "Selective registry operator differs from configured signing key");
    System.out.println("SelectiveDisclosureRegistry at: " + address);
  }

  public String address() {
    return address;
  }

  public String operator() {
    return gateway.operator;
  }

  public long chainId() {
    return gateway.chainId;
  }

  private Bytes32 b(String hex) {
    return new Bytes32(MerkleTreeService.hex32(hex));
  }

  private List<Type> read(Function function) throws Exception {
    var call =
        web3j
            .ethCall(
                Transaction.createEthCallTransaction(
                    operator(), address, FunctionEncoder.encode(function)),
                DefaultBlockParameterName.LATEST)
            .send();
    if (call.hasError() || call.isReverted()) throw new IllegalStateException("Chain read failed");
    var result = FunctionReturnDecoder.decode(call.getValue(), function.getOutputParameters());
    if (result.size() != function.getOutputParameters().size())
      throw new IllegalStateException("Unexpected contract response");
    return result;
  }

  public ChainAnchor get(String id) throws Exception {
    var f =
        new Function(
            "getCredential",
            List.of(b(id)),
            List.of(
                new TypeReference<Bytes32>() {},
                new TypeReference<Bytes32>() {},
                new TypeReference<Bytes32>() {},
                new TypeReference<Address>() {},
                new TypeReference<Uint64>() {},
                new TypeReference<Uint32>() {},
                new TypeReference<Uint8>() {},
                new TypeReference<Uint8>() {},
                new TypeReference<Bytes32>() {}));
    var r = read(f);
    return new ChainAnchor(
        Numeric.toHexString((byte[]) r.get(0).getValue()),
        Numeric.toHexString((byte[]) r.get(1).getValue()),
        Numeric.toHexString((byte[]) r.get(2).getValue()),
        r.get(3).getValue().toString(),
        Instant.ofEpochSecond(((BigInteger) r.get(4).getValue()).longValueExact()),
        ((BigInteger) r.get(5).getValue()).intValueExact(),
        ((BigInteger) r.get(6).getValue()).intValueExact(),
        ((BigInteger) r.get(7).getValue()).intValueExact(),
        Numeric.toHexString((byte[]) r.get(8).getValue()));
  }

  public synchronized String anchor(
      String id,
      String root,
      String doc,
      String provenance,
      int version,
      int level,
      String previous)
      throws Exception {
    ChainAnchor existing = get(id);
    if (existing.status() != 0) {
      if (!existing.root().equals(root)
          || !existing.documentCommitment().equals(doc)
          || !existing.provenanceDigest().equals(provenance)
          || existing.version() != version
          || existing.provenanceLevel() != level
          || existing.status() != 1
          || !existing.owner().equalsIgnoreCase(operator()))
        throw new IllegalStateException("Anchor already exists with different state");
      return null; // Receipt lost after mining: recover by independently reading the existing
                   // anchor.
    }
    var f =
        new Function(
            "registerCredential",
            List.of(
                b(id),
                b(root),
                b(doc),
                b(provenance),
                new Uint32(version),
                new Uint8(level),
                b(previous == null ? ZERO : previous)),
            List.of());
    return gateway.send(address, FunctionEncoder.encode(f)).getTransactionHash();
  }

  public synchronized void revoke(String id) throws Exception {
    if (get(id).status() == 2) return;
    gateway.send(
        address,
        FunctionEncoder.encode(new Function("revokeCredential", List.of(b(id)), List.of())));
  }
}
