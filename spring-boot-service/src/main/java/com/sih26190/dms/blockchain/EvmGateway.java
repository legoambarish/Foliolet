package com.sih26190.dms.blockchain;

import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;
import org.web3j.crypto.Credentials;
import org.web3j.protocol.Web3j;
import org.web3j.protocol.core.DefaultBlockParameterName;
import org.web3j.protocol.core.methods.response.TransactionReceipt;
import org.web3j.tx.RawTransactionManager;
import org.web3j.tx.gas.ContractGasProvider;
import org.web3j.tx.response.PollingTransactionReceiptProcessor;
import org.web3j.utils.Numeric;

/** Both registries share one serialized signer/nonce stream in this process. */
@Component
public class EvmGateway {
  private final Web3j web3j;
  private final RawTransactionManager manager;
  private final ContractGasProvider gas;
  private final Path state;
  public final long chainId;
  public final String operator;

  public EvmGateway(
      Web3j web3j,
      Credentials credentials,
      ContractGasProvider gas,
      @Value("${wallet.data-dir:../.local-data}") String dataDir,
      @Value("${blockchain.expected-chain-id:1337}") long expectedId)
      throws Exception {
    this.web3j = web3j;
    this.gas = gas;
    state = Paths.get(dataDir, "chain");
    chainId = web3j.ethChainId().send().getChainId().longValueExact();
    if (chainId != expectedId)
      throw new IllegalStateException("RPC chain ID differs from expected chain ID");
    operator = credentials.getAddress();
    manager = new RawTransactionManager(web3j, credentials, chainId);
  }

  public synchronized TransactionReceipt send(String to, String data) throws Exception {
    var sent =
        manager.sendTransaction(gas.getGasPrice(), gas.getGasLimit(), to, data, BigInteger.ZERO);
    if (sent.hasError())
      throw new IllegalStateException("EVM transaction rejected: " + sent.getError().getMessage());
    var receipt =
        new PollingTransactionReceiptProcessor(web3j, 500, 80)
            .waitForTransactionReceipt(sent.getTransactionHash());
    if (!receipt.isStatusOK())
      throw new IllegalStateException("EVM transaction reverted: " + receipt.getTransactionHash());
    return receipt;
  }

  public synchronized String deployment(String name, String configured) throws Exception {
    Files.createDirectories(state);
    Path file = state.resolve(name + "-" + chainId + "-" + operator + ".address");
    String address = configured;
    if (address == null || address.isBlank())
      address = Files.exists(file) ? Files.readString(file).strip() : "";
    if (!address.isBlank()) {
      requireCode(address);
      return address;
    }
    try (var stream =
        new ClassPathResource("solidity/" + name + "/" + name + ".bin").getInputStream()) {
      address =
          send(
                  null,
                  Numeric.prependHexPrefix(
                      new String(stream.readAllBytes(), StandardCharsets.UTF_8).strip()))
              .getContractAddress();
    }
    requireCode(address);
    Files.writeString(file, address, StandardOpenOption.CREATE_NEW);
    return address;
  }

  public void requireCode(String address) throws Exception {
    if (!address.matches("0x[0-9a-fA-F]{40}"))
      throw new IllegalStateException("Invalid contract address");
    var response = web3j.ethGetCode(address, DefaultBlockParameterName.LATEST).send();
    if (response.hasError() || response.getCode() == null || response.getCode().equals("0x"))
      throw new IllegalStateException(
          "Configured/persisted contract missing from chain; check RPC or restore chain data");
  }
}
