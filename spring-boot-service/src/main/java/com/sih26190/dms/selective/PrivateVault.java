package com.sih26190.dms.selective;

import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import javax.crypto.Cipher;
import javax.crypto.spec.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.web3j.crypto.Hash;
import org.web3j.utils.Numeric;

/** Custodial encryption. The platform can decrypt; this is not end-to-end encryption. */
@Component
public class PrivateVault {
  private final byte[] key;
  private final SecureRandom random = new SecureRandom();
  public final Path root;

  public PrivateVault(
      @Value("${wallet.data-dir:../.local-data}") String dataDir,
      @Value("${wallet.encryption-key:}") String configuredKey)
      throws Exception {
    root = Paths.get(dataDir).toAbsolutePath().normalize();
    Files.createDirectories(root);
    if (!configuredKey.isBlank()) key = Base64.getDecoder().decode(configuredKey);
    else {
      Path keyFile = root.resolve("vault.key");
      if (!Files.exists(keyFile)) {
        byte[] generated = new byte[32];
        random.nextBytes(generated);
        Files.write(keyFile, generated, StandardOpenOption.CREATE_NEW);
      }
      key = Files.readAllBytes(keyFile);
    }
    if (key.length != 32)
      throw new IllegalArgumentException("Wallet encryption key must contain 32 bytes");
  }

  public byte[] encrypt(byte[] plaintext, String context) {
    try {
      byte[] nonce = new byte[12];
      random.nextBytes(nonce);
      Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
      cipher.init(
          Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(128, nonce));
      cipher.updateAAD(context.getBytes(StandardCharsets.UTF_8));
      byte[] encrypted = cipher.doFinal(plaintext);
      byte[] result = new byte[nonce.length + encrypted.length];
      System.arraycopy(nonce, 0, result, 0, 12);
      System.arraycopy(encrypted, 0, result, 12, encrypted.length);
      return result;
    } catch (GeneralSecurityException e) {
      throw new IllegalStateException("Encryption failed", e);
    }
  }

  public byte[] decrypt(byte[] encrypted, String context) {
    try {
      if (encrypted.length < 28) throw new GeneralSecurityException("Invalid ciphertext");
      Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
      cipher.init(
          Cipher.DECRYPT_MODE,
          new SecretKeySpec(key, "AES"),
          new GCMParameterSpec(128, Arrays.copyOf(encrypted, 12)));
      cipher.updateAAD(context.getBytes(StandardCharsets.UTF_8));
      return cipher.doFinal(Arrays.copyOfRange(encrypted, 12, encrypted.length));
    } catch (GeneralSecurityException e) {
      throw new IllegalStateException("Private data failed authentication", e);
    }
  }

  public String seal(String text, String context) {
    return Base64.getEncoder()
        .encodeToString(encrypt(text.getBytes(StandardCharsets.UTF_8), context));
  }

  public String open(String encrypted, String context) {
    return new String(
        decrypt(Base64.getDecoder().decode(encrypted), context), StandardCharsets.UTF_8);
  }

  public Path store(String id, byte[] bytes) throws java.io.IOException {
    Path files = root.resolve("wallet/files"), backups = root.resolve("wallet/backups");
    Files.createDirectories(files);
    Files.createDirectories(backups);
    byte[] encrypted = encrypt(bytes, id);
    Path file = files.resolve(id + ".enc");
    Files.write(file, encrypted, StandardOpenOption.CREATE_NEW);
    Files.write(backups.resolve(id + ".enc"), encrypted, StandardOpenOption.CREATE_NEW);
    return file;
  }

  public Path backup(String id) {
    return root.resolve("wallet/backups/" + id + ".enc");
  }

  public byte[] read(String filename, String id) throws java.io.IOException {
    Path path = Paths.get(filename).toAbsolutePath().normalize();
    if (!path.startsWith(root.resolve("wallet")))
      throw new IllegalArgumentException("Invalid vault path");
    return decrypt(Files.readAllBytes(path), id);
  }

  public static String sha256(byte[] bytes) {
    try {
      return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
    } catch (GeneralSecurityException e) {
      throw new IllegalStateException(e);
    }
  }

  public static String commitment(String salt, String documentHash) {
    byte[] bytes = new byte[65];
    bytes[0] = 2;
    System.arraycopy(MerkleTreeService.hex32(salt), 0, bytes, 1, 32);
    System.arraycopy(MerkleTreeService.hex32(documentHash), 0, bytes, 33, 32);
    return Numeric.toHexString(Hash.sha3(bytes));
  }
}
