package com.sih26190.dms.selective;

import java.io.RandomAccessFile;
import java.nio.file.*;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.Arrays;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

class PrivateVaultSecurityTest {
    @TempDir Path temp;
    private PrivateVault vault() throws Exception { return new PrivateVault(temp.resolve("state").toString(), ""); }
    private static byte[] original() { return "Fictional private record".getBytes(java.nio.charset.StandardCharsets.UTF_8); }
    private void symlinks() { assumeTrue(!System.getProperty("os.name").toLowerCase().contains("windows")); }

    @Test void restartPreservesOriginalKeyCiphertextAndBackup() throws Exception {
        var first = vault(); var file = first.store("document-1", original());
        var key = Files.readAllBytes(first.root.resolve("vault.key"));
        var ciphertext = Files.readAllBytes(file);
        var second = vault();
        assertArrayEquals(key, Files.readAllBytes(second.root.resolve("vault.key")));
        assertArrayEquals(ciphertext, Files.readAllBytes(file));
        assertArrayEquals(original(), second.read(file.toString(), "document-1"));
        assertArrayEquals(original(), second.read(second.backup("document-1").toString(), "document-1"));
        assertThrows(FileAlreadyExistsException.class, () -> second.store("document-1", original()));
    }
    @Test void documentIdsCannotEscapeStorage() throws Exception {
        var v = vault();
        for (String id : new String[]{"../escape", "../../escape", "/tmp/escape", "a/b", "a\\b", "", ".."}) {
            assertThrows(IllegalArgumentException.class, () -> v.store(id, original()), id);
            assertThrows(IllegalArgumentException.class, () -> v.backup(id), id);
        }
    }
    @Test void aSymlinkedOriginalCannotReadOutsideVaultEvenWithValidCiphertext() throws Exception {
        symlinks(); var v = vault(); var file = v.store("document-1", original());
        var outside = temp.resolve("outside.enc"); Files.copy(file, outside); Files.delete(file);
        Files.createSymbolicLink(file, outside);
        assertThrows(Exception.class, () -> v.read(file.toString(), "document-1"));
    }
    @Test void aSymlinkedParentCannotRedirectReadsOrNewWrites() throws Exception {
        symlinks(); var v = vault(); var file = v.store("document-1", original());
        var outside = temp.resolve("outside"); Files.move(file.getParent(), outside);
        Files.createSymbolicLink(file.getParent(), outside);
        assertThrows(Exception.class, () -> v.read(file.toString(), "document-1"));
        assertThrows(Exception.class, () -> v.store("document-2", original()));
        assertFalse(Files.exists(outside.resolve("document-2.enc")));
    }
    @Test void aSymlinkedKeyIsRejectedWithoutChangingItsTarget() throws Exception {
        symlinks(); var v = vault(); var key = v.root.resolve("vault.key");
        var expected = Files.readAllBytes(key); var outside = temp.resolve("outside.key");
        Files.move(key, outside); Files.createSymbolicLink(key, outside);
        assertThrows(Exception.class, this::vault);
        assertArrayEquals(expected, Files.readAllBytes(outside));
    }
    @Test void keysDirectoriesAndCiphertextsAreOwnerOnlyOnPosix() throws Exception {
        assumeTrue(temp.getFileSystem().supportedFileAttributeViews().contains("posix"));
        var v = vault(); var file = v.store("document-1", original());
        for (Path directory : new Path[]{v.root, v.root.resolve("wallet"), file.getParent(), v.backup("document-1").getParent()})
            assertEquals(PosixFilePermissions.fromString("rwx------"), Files.getPosixFilePermissions(directory));
        for (Path privateFile : new Path[]{v.root.resolve("vault.key"), file, v.backup("document-1")})
            assertEquals(PosixFilePermissions.fromString("rw-------"), Files.getPosixFilePermissions(privateFile));
    }
    @Test void oversizedCiphertextIsRejectedBeforeUnboundedAllocation() throws Exception {
        var v = vault(); var file = v.store("document-1", original());
        try (var sparse = new RandomAccessFile(file.toFile(), "rw")) { sparse.setLength(21L * 1024 * 1024); }
        var error = assertThrows(java.io.IOException.class, () -> v.read(file.toString(), "document-1"));
        assertTrue(error.getMessage().contains("limit"));
    }
    @Test void ciphertextAndContextTamperingRemainRejected() throws Exception {
        var v = vault(); var cipher = v.encrypt(original(), "document-1");
        assertFalse(Arrays.equals(original(), cipher));
        assertThrows(IllegalStateException.class, () -> v.decrypt(cipher, "document-2"));
        cipher[cipher.length - 1] ^= 1;
        assertThrows(IllegalStateException.class, () -> v.decrypt(cipher, "document-1"));
    }
}
