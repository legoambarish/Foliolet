package com.sih26190.dms.service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import com.sih26190.dms.blockchain.BlockchainService;
import com.sih26190.dms.dto.DocumentResponse;
import com.sih26190.dms.dto.UpdateDocumentRequest;
import com.sih26190.dms.dto.VerifyResponse;
import com.sih26190.dms.model.CandidateHash;
import com.sih26190.dms.model.DocumentRecord;
import com.sih26190.dms.model.Role;
import com.sih26190.dms.model.User;
import com.sih26190.dms.repository.CandidateHashRepository;
import com.sih26190.dms.repository.DocumentRecordRepository;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class DocumentService {

    private final DocumentRecordRepository documentRecordRepository;
    private final CandidateHashRepository candidateHashRepository;
    private final AuditService auditService;
    private final BlockchainService blockchainService;

    @Value("${dms.storage.location}")
    private String storageLocation;
    @Value("${dms.backup.location}")
    private String backupLocation;
    /**

     * Also checks CandidateHashRepository for an earlier, independent
     * hash of a file with this same name, captured locally by the
     * watcher script before this upload happened. A mismatch means the
     * file was altered on the officer's machine between first being
     * seen there and being uploaded, this is caught and flagged here,
     * separate from the on-chain post-upload tamper check in verify().
     */
    @Transactional
    public DocumentResponse upload(MultipartFile file, String caseId, String documentType, User uploader) {
        try {
            byte[] fileBytes = file.getBytes();

            Path directory = Paths.get(storageLocation);
            Files.createDirectories(directory);

            String storedFileName = UUID.randomUUID().toString();
            Path destination = directory.resolve(storedFileName);
            Files.write(destination, fileBytes);

// NEW — keep a known-good backup copy at upload time
            Path backupDir = Paths.get(backupLocation);
            Files.createDirectories(backupDir);
            Path backupDestination = backupDir.resolve(storedFileName);

            Files.write(backupDestination, fileBytes);

            DocumentRecord document = new DocumentRecord();
            document.setCaseId(caseId);
            document.setDocumentType(documentType);
            document.setFilePath(destination.toString());
            document.setBackupFilePath(backupDestination.toString());  // NEW
            document.setOriginalFileName(file.getOriginalFilename());
            document.setUploadedBy(uploader);
            document.setUploadedAt(LocalDateTime.now());

            DocumentRecord saved = documentRecordRepository.save(document);

            auditService.log(uploader, saved, "UPLOAD");

            try {
                blockchainService.storeDocumentHash(saved.getId(), fileBytes, caseId);
            } catch (Exception e) {
                throw new RuntimeException("Failed to anchor document hash on-chain, upload rolled back", e);
            }

            String preUploadWarning = checkAgainstCandidateHash(file.getOriginalFilename(), fileBytes, saved, uploader);

            return toResponse(saved, preUploadWarning);
        } catch (IOException e) {
            throw new RuntimeException("Failed to store uploaded file", e);
        }
    }

    /**
     * Returns a warning message if a mismatch was found, null if it
     * matched or no candidate record exists (e.g. the watcher was not
     * running, or the file was never in the watched folder, in which
     * case no claim either way can be made).
     */
    private String checkAgainstCandidateHash(String filename, byte[] uploadedBytes, DocumentRecord saved, User uploader) {
        Optional<CandidateHash> candidate = candidateHashRepository.findFirstByFilenameAndOwnerIdOrderByCapturedAtAsc(filename, uploader.getId());

        if (candidate.isEmpty()) {
            return null;
        }

        String uploadedHash = sha256Hex(uploadedBytes);
        String candidateHash = candidate.get().getSha256Hash();

        if (uploadedHash.equalsIgnoreCase(candidateHash)) {
            return null;
        }

        auditService.log(uploader, saved, "PRE_UPLOAD_TAMPER_DETECTED");

        return "This file's content differs from the version first observed locally at "
                + candidate.get().getCapturedAt()
                + ". It may have been modified after creation but before upload.";
    }

    private String sha256Hex(byte[] bytes) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(bytes);
            StringBuilder hex = new StringBuilder();
            for (byte b : hash) {
                hex.append(String.format("%02x", b));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }

    public void recordCandidateHash(String filename, String sha256Hash, User owner) {
        CandidateHash candidateHash = new CandidateHash();
        if (filename == null || filename.isBlank() || sha256Hash == null || !sha256Hash.matches("[0-9a-fA-F]{64}")) throw new IllegalArgumentException("Invalid fingerprint");
        candidateHash.setOwnerId(owner.getId());
        candidateHash.setFilename(filename);
        candidateHash.setSha256Hash(sha256Hash);
        candidateHash.setCapturedAt(LocalDateTime.now());
        candidateHashRepository.save(candidateHash);
    }

    /**
     * OFFICER sees only their own uploads. ADMIN sees everything.
     */
    public List<DocumentResponse> listForUser(User requester) {
        List<DocumentRecord> records = requester.getRole() == Role.ADMIN
                ? documentRecordRepository.findAll()
                : documentRecordRepository.findByUploadedBy(requester);

        return records.stream().map(d -> toResponse(d, null)).toList();
    }

    /**
     * Enforces per-document access before returning it, and logs the view
     * regardless of whether access is granted or denied.
     */
    @Transactional
    public DocumentResponse getById(Long id, User requester) {
        DocumentRecord document = documentRecordRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Document not found"));

        requireOwnerOrAdmin(document, requester);

        auditService.log(requester, document, "VIEW");

        return toResponse(document, null);
    }

    /**
     * Recomputes the on-disk file's hash right now and compares it
     * against what was anchored on-chain at upload time. A mismatch
     * means the file was altered outside the system after upload.
     * Logs a VERIFY action either way.
     */
    @Transactional
    public VerifyResponse verify(Long id, User requester) {
        DocumentRecord document = documentRecordRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Document not found"));

        requireOwnerOrAdmin(document, requester);

        byte[] currentBytes;
        try {
            currentBytes = Files.readAllBytes(Paths.get(document.getFilePath()));
        } catch (IOException e) {
            throw new RuntimeException("Could not read file from disk to verify it", e);
        }

        boolean matches;
        try {
            matches = blockchainService.verifyDocumentHash(id, currentBytes);
        } catch (Exception e) {
            throw new RuntimeException("Could not reach the blockchain to verify this document", e);
        }

        boolean restored = false;
        String message;

        if (matches) {
            message = "File matches the hash recorded on-chain at upload time.";
        } else if (document.getBackupFilePath() != null) {
            try {
                byte[] backupBytes = Files.readAllBytes(Paths.get(document.getBackupFilePath()));
                try {
                    if (!blockchainService.verifyDocumentHash(id, backupBytes)) throw new IOException("Backup does not match anchor");
                } catch (IOException e) { throw e; }
                catch (Exception e) { throw new IOException("Cannot validate backup", e); }
                Files.copy(
                        Paths.get(document.getBackupFilePath()),
                        Paths.get(document.getFilePath()),
                        java.nio.file.StandardCopyOption.REPLACE_EXISTING
                );
                restored = true;
                auditService.log(requester, document, "AUTO_RESTORED");
                message = "File did NOT match the on-chain record and has been restored to its last known-good version.";
            } catch (IOException e) {
                message = "File does NOT match the on-chain record, it may have been altered since upload. Restore from backup also failed.";
            }
        } else {
            message = "File does NOT match the on-chain record, it may have been altered since upload. No backup was available to restore from.";
        }

        auditService.log(requester, document, "VERIFY");

        return new VerifyResponse(id, !matches, restored, message);
    }


    @Transactional
    public DocumentResponse update(Long id, UpdateDocumentRequest request, User requester) {
        DocumentRecord document = documentRecordRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Document not found"));

        requireOwnerOrAdmin(document, requester);

        if (request.getCaseId() != null && !request.getCaseId().isBlank()) {
            document.setCaseId(request.getCaseId());
        }
        if (request.getDocumentType() != null && !request.getDocumentType().isBlank()) {
            document.setDocumentType(request.getDocumentType());
        }

        DocumentRecord saved = documentRecordRepository.save(document);
        auditService.log(requester, saved, "UPDATE");

        return toResponse(saved, null);
    }

    /**
     * Deletes the metadata row and the underlying file. The audit log
     * entry is written first, capturing the document's id and caseId as
     * plain values (see AuditLog), so the audit trail survives even
     * though the DocumentRecord row itself is removed right after.
     * The on-chain hash record is intentionally left in place, since
     * the blockchain layer is append-only by design, this is itself a
     * useful property: even a deleted document's integrity history is
     * still verifiable if the file is recovered from a backup later.
     */
    @Transactional
    public void delete(Long id, User requester) {
        DocumentRecord document = documentRecordRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Document not found"));

        requireOwnerOrAdmin(document, requester);

        auditService.log(requester, document, "DELETE");

        try {
            Files.deleteIfExists(Paths.get(document.getFilePath()));
        } catch (IOException e) {
            throw new RuntimeException("Failed to delete file from disk", e);
        }

        documentRecordRepository.delete(document);
    }

    private void requireOwnerOrAdmin(DocumentRecord document, User requester) {
        boolean isOwner = document.getUploadedBy().getId().equals(requester.getId());
        boolean isAdmin = requester.getRole() == Role.ADMIN;

        if (!isOwner && !isAdmin) {
            throw new AccessDeniedException("You do not have access to this document");
        }
    }

    private DocumentResponse toResponse(DocumentRecord document, String preUploadWarning) {
        return new DocumentResponse(
                document.getId(),
                document.getCaseId(),
                document.getDocumentType(),
                document.getOriginalFileName(),
                document.getUploadedBy().getUsername(),
                document.getUploadedAt(),
                preUploadWarning
        );
    }

}