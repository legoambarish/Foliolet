package com.sih26190.dms.controller;

import java.util.List;

import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import com.sih26190.dms.dto.DocumentResponse;
import com.sih26190.dms.dto.UpdateDocumentRequest;
import com.sih26190.dms.model.User;
import com.sih26190.dms.repository.UserRepository;
import com.sih26190.dms.service.DocumentService;

import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api/documents")
@RequiredArgsConstructor
public class DocumentController {

    private final DocumentService documentService;
    private final UserRepository userRepository;

    @PostMapping
    public DocumentResponse upload(
            @RequestParam("file") MultipartFile file,
            @RequestParam("caseId") String caseId,
            @RequestParam("documentType") String documentType,
            Authentication authentication) {

        User uploader = currentUser(authentication);
        return documentService.upload(file, caseId, documentType, uploader);
    }
    @PostMapping("/candidate-hash")
    public void recordCandidateHash(@RequestBody com.sih26190.dms.dto.CandidateHashRequest request, Authentication authentication) {
        documentService.recordCandidateHash(request.getFilename(), request.getSha256Hash(), currentUser(authentication));
    }

    @GetMapping
    public List<DocumentResponse> list(Authentication authentication) {
        User requester = currentUser(authentication);
        return documentService.listForUser(requester);
    }

    @GetMapping("/{id}")
    public DocumentResponse getById(@PathVariable Long id, Authentication authentication) {
        User requester = currentUser(authentication);
        return documentService.getById(id, requester);
    }

   //versioning aint possible for now
    @PutMapping("/{id}")
    public DocumentResponse update(
            @PathVariable Long id,
            @RequestBody UpdateDocumentRequest request,
            Authentication authentication) {

        User requester = currentUser(authentication);
        return documentService.update(id, request, requester);
    }


    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id, Authentication authentication) {
        User requester = currentUser(authentication);
        documentService.delete(id, requester);
        return ResponseEntity.noContent().build();
    }


    private User currentUser(Authentication authentication) {
        String username = authentication.getName();
        return userRepository.findByUsername(username)
                .orElseThrow(() -> new RuntimeException("Authenticated user not found: " + username));
    }
    @GetMapping("/{id}/verify")
    public com.sih26190.dms.dto.VerifyResponse verify(@PathVariable Long id, Authentication authentication) {
        User requester = currentUser(authentication);
        return documentService.verify(id, requester);
    }

}
