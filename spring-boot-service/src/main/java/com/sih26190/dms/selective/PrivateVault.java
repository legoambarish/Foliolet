package com.sih26190.dms.selective;

import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.io.IOException;
import java.security.*;
import java.util.*;
import javax.crypto.Cipher;
import javax.crypto.spec.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.web3j.crypto.Hash;
import org.web3j.utils.Numeric;


@Component
public class PrivateVault {
  private static final int MAX_PLAINTEXT_BYTES = 20 * 1024 * 1024;
  private static final int MAX_CIPHERTEXT_BYTES = MAX_PLAINTEXT_BYTES + 28;
  private final byte[] key;
  private final SecureRandom random = new SecureRandom();
  public final Path root;

  public PrivateVault(
      @Value("${wallet.data-dir:../.local-data}") String dataDir,
      @Value("${wallet.encryption-key:}") String configuredKey)
      throws Exception {
    Path configuredRoot = Paths.get(dataDir).toAbsolutePath().normalize();
    privateDirectory(configuredRoot);
    root = configuredRoot.toRealPath();
    if (!configuredKey.isBlank()) key = Base64.getDecoder().decode(configuredKey);
    else {
      Path keyFile = root.resolve("vault.key");
      if (!Files.exists(keyFile, LinkOption.NOFOLLOW_LINKS)) {
        byte[] generated = new byte[32];
        random.nextBytes(generated);
        try { writeNewPrivate(keyFile, generated); }
        catch (FileAlreadyExistsException concurrentCreator) {
          // Never replace or regenerate another process's key.
        }
      }
      if (!Files.isRegularFile(keyFile, LinkOption.NOFOLLOW_LINKS))
        throw new IOException("The vault key must be a regular local file");
      privatePermissions(keyFile, false);
      try (var input = Files.newInputStream(keyFile, LinkOption.NOFOLLOW_LINKS)) {
        key = input.readNBytes(33);
      }
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

  /** Limits apply to originals, not to short encrypted metadata sealed above. */
  public Path store(String id, byte[] bytes) throws IOException {
    validId(id);
    if (bytes == null || bytes.length > MAX_PLAINTEXT_BYTES)
      throw new IOException("The private original exceeds the vault size limit");
    Path wallet = root.resolve("wallet");
    Path files = wallet.resolve("files"), backups = wallet.resolve("backups");
    for (Path directory : new Path[]{wallet, files, backups}) {
      privateDirectory(directory);
      if (!directory.toRealPath().equals(directory))
        throw new IOException("Invalid private storage directory");
    }
    byte[] encrypted = encrypt(bytes, id);
    Path file = files.resolve(id + ".enc");
    writeNewPrivate(file, encrypted);
    writeNewPrivate(backups.resolve(id + ".enc"), encrypted);
    return file;
  }

  public Path backup(String id) {
    validId(id);
    return root.resolve("wallet/backups").resolve(id + ".enc");
  }

  public byte[] read(String filename, String id) throws IOException {
    validId(id);
    Path path = Paths.get(filename).toAbsolutePath().normalize();
    Path wallet = root.resolve("wallet");
    Path parent = path.getParent();
    if (!(wallet.resolve("files").equals(parent) || wallet.resolve("backups").equals(parent))
        || !path.getFileName().toString().equals(id + ".enc"))
      throw new IllegalArgumentException("Invalid vault path");
    // Checking every controlled directory blocks parent symlinks/junction escapes.
    // Owner-only directories are the OS boundary; this is not protection against root.
    for (Path directory : new Path[]{root, wallet, parent}) {
      if (!Files.isDirectory(directory, LinkOption.NOFOLLOW_LINKS)
          || !directory.toRealPath().equals(directory))
        throw new IOException("Invalid private storage directory");
    }
    if (!Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS))
      throw new IOException("The private original must be a regular local file");
    if (Files.size(path) > MAX_CIPHERTEXT_BYTES)
      throw new IOException("The private original exceeds the vault size limit");
    try (var input = Files.newInputStream(path, LinkOption.NOFOLLOW_LINKS)) {
      byte[] encrypted = input.readNBytes(MAX_CIPHERTEXT_BYTES + 1);
      if (encrypted.length > MAX_CIPHERTEXT_BYTES)
        throw new IOException("The private original exceeds the vault size limit");
      return decrypt(encrypted, id);
    }
  }

  private static void validId(String id) {
    if (id == null || !id.matches("[A-Za-z0-9_-]{1,128}"))
      throw new IllegalArgumentException("Invalid private document identifier");
  }

  private static FileAttribute<?>[] attributes(Path path, boolean directory) {
    if (!path.getFileSystem().supportedFileAttributeViews().contains("posix"))
      return new FileAttribute<?>[0];
    return new FileAttribute<?>[]{PosixFilePermissions.asFileAttribute(
        PosixFilePermissions.fromString(directory ? "rwx------" : "rw-------"))};
  }

  private static void privatePermissions(Path path, boolean directory) throws IOException {
    if (path.getFileSystem().supportedFileAttributeViews().contains("posix"))
      Files.setPosixFilePermissions(path, PosixFilePermissions.fromString(
          directory ? "rwx------" : "rw-------"));
    // Windows relies on the private user's directory ACL; never pretend POSIX chmod applies.
  }

  private static void privateDirectory(Path path) throws IOException {
    if (Files.isSymbolicLink(path)) throw new IOException("Private storage cannot use a symlink");
    Files.createDirectories(path, attributes(path, true));
    if (!Files.isDirectory(path, LinkOption.NOFOLLOW_LINKS))
      throw new IOException("Invalid private storage directory");
    privatePermissions(path, true);
  }

  private static void writeNewPrivate(Path path, byte[] bytes) throws IOException {
    try (var channel = Files.newByteChannel(path,
        Set.of(StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS),
        attributes(path, false))) {
      var buffer = java.nio.ByteBuffer.wrap(bytes);
      while (buffer.hasRemaining()) channel.write(buffer);
    }
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
