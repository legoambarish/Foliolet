package com.sih26190.dms.service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.stereotype.Service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sih26190.dms.dto.AiAnalysisResponse;
import com.sih26190.dms.model.AiInsight;
import com.sih26190.dms.model.DocumentRecord;
import com.sih26190.dms.model.Role;
import com.sih26190.dms.model.User;
import com.sih26190.dms.repository.AiInsightRepository;
import com.sih26190.dms.repository.DocumentRecordRepository;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;

import lombok.RequiredArgsConstructor;


@Service
@RequiredArgsConstructor
public class AiAnalysisService {

    private final DocumentRecordRepository documentRecordRepository;
    private final AiInsightRepository aiInsightRepository;
    private final TextExtractionService textExtractionService;
    private final AuditService auditService;

    @Value("${openrouter.api-key}")
    private String openRouterApiKey;

    @Value("${openrouter.model}")
    private String openRouterModel;

    private final ObjectMapper objectMapper = new ObjectMapper().registerModule(new JavaTimeModule());
    private final HttpClient httpClient = HttpClient.newHttpClient();

    public AiAnalysisResponse analyze(Long documentId, User requester) {
        DocumentRecord document = documentRecordRepository.findById(documentId)
                .orElseThrow(() -> new RuntimeException("Document not found"));

        requireOwnerOrAdmin(document, requester);

        String documentText;
        try {
            documentText = textExtractionService.extractText(
                    Paths.get(document.getFilePath()), document.getOriginalFileName());
        } catch (Exception e) {
            throw new RuntimeException("Failed to extract text from document", e);
        }

        if (documentText == null || documentText.isBlank()) {
            throw new RuntimeException("No extractable text found in this document");
        }

        String rawModelOutput;
        try {
            rawModelOutput = callOpenRouter(documentText);
        } catch (Exception e) {
            saveInsight(documentId, requester, "FAILED", "{\"error\":\"analysis call failed\"}");
            throw new RuntimeException("AI analysis call failed", e);
        }

        AiAnalysisResponse response = parseAndVerify(rawModelOutput, documentText, documentId);

        String resultJson;
        try {
            resultJson = objectMapper.writeValueAsString(response);
        } catch (Exception e) {
            throw new RuntimeException("Failed to serialize analysis result", e);
        }

        saveInsight(documentId, requester, "COMPLETE", resultJson);
        auditService.log(requester, document, "AI_ANALYSIS_RUN");

        return response;
    }

    public AiAnalysisResponse getLatest(Long documentId, User requester) {
        DocumentRecord document = documentRecordRepository.findById(documentId)
                .orElseThrow(() -> new RuntimeException("Document not found"));

        requireOwnerOrAdmin(document, requester);

        return aiInsightRepository.findFirstByDocumentIdOrderByCreatedAtDesc(documentId)
                .filter(insight -> "COMPLETE".equals(insight.getStatus()))
                .map(insight -> {
                    try {
                        return objectMapper.readValue(insight.getResultJson(), AiAnalysisResponse.class);
                    } catch (Exception e) {
                        throw new RuntimeException("Failed to parse stored analysis", e);
                    }
                })
                .orElse(null);
    }

    private String callOpenRouter(String documentText) throws Exception {
        String prompt = buildPrompt(documentText);
        String requestBody = objectMapper.writeValueAsString(new OpenRouterRequest(openRouterModel, prompt));

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create("https://openrouter.ai/api/v1/chat/completions"))
                .header("Authorization", "Bearer " + openRouterApiKey)
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() != 200) {
            throw new RuntimeException("OpenRouter returned status " + response.statusCode() + ": " + response.body());
        }

        JsonNode root = objectMapper.readTree(response.body());
        return root.at("/choices/0/message/content").asText();
    }

    private String buildPrompt(String documentText) {
        return """
                You are analyzing a legal/investigation document for a case management system.
                Read the following document text carefully and extract information a busy reviewer might miss.
                Respond ONLY with valid JSON in exactly this shape, no other text, no markdown fences:

                {
                  "summary": "2-3 sentence plain-language summary of what this document is and contains",
                  "keyDates": [{"date": "the date as written", "context": "the exact sentence it appears in, quoted verbatim from the document"}],
                  "keyParties": [{"name": "person or entity name", "context": "the exact sentence they are mentioned in, quoted verbatim"}],
                  "flaggedClauses": [{"quote": "an exact sentence or clause quoted verbatim from the document", "concern": "why this detail is easy to overlook or worth a reviewer's attention"}]
                }

                Rules:
                - Every "context" and "quote" field must be an exact, verbatim substring of the document text below. Do not paraphrase these fields.
                - If you cannot find a genuine example for a category, return an empty list for it, do not invent one.
                - Respond with JSON only.

                Document text:
                \"\"\"
                %s
                \"\"\"
                """.formatted(documentText);
    }
//    clean ts up, parse and verify:
    private AiAnalysisResponse parseAndVerify(String rawModelOutput, String documentText, Long documentId) {
        String cleaned = rawModelOutput.trim();
        if (cleaned.startsWith("```")) {
            cleaned = cleaned.replaceAll("^```[a-zA-Z]*\\n", "").replaceAll("```$", "").trim();
        }

        JsonNode root;
        try {
            root = objectMapper.readTree(cleaned);
        } catch (Exception e) {
            throw new RuntimeException("Model did not return valid JSON: " + e.getMessage());
        }

        String normalizedDocText = normalizeForMatch(documentText);

        AiAnalysisResponse response = new AiAnalysisResponse();
        response.setDocumentId(documentId);
        response.setSummary(root.path("summary").asText(""));
        response.setAnalyzedAt(LocalDateTime.now());

        List<AiAnalysisResponse.KeyDate> keyDates = new ArrayList<>();
        for (JsonNode node : root.path("keyDates")) {
            String context = node.path("context").asText("");
            if (containsVerbatim(normalizedDocText, context)) {
                keyDates.add(new AiAnalysisResponse.KeyDate(node.path("date").asText(""), context));
            }
        }
        response.setKeyDates(keyDates);

        List<AiAnalysisResponse.KeyParty> keyParties = new ArrayList<>();
        for (JsonNode node : root.path("keyParties")) {
            String context = node.path("context").asText("");
            if (containsVerbatim(normalizedDocText, context)) {
                keyParties.add(new AiAnalysisResponse.KeyParty(node.path("name").asText(""), context));
            }
        }
        response.setKeyParties(keyParties);

        List<AiAnalysisResponse.FlaggedClause> flaggedClauses = new ArrayList<>();
        for (JsonNode node : root.path("flaggedClauses")) {
            String quote = node.path("quote").asText("");
            if (containsVerbatim(normalizedDocText, quote)) {
                flaggedClauses.add(new AiAnalysisResponse.FlaggedClause(quote, node.path("concern").asText("")));
            }
        }
        response.setFlaggedClauses(flaggedClauses);

        return response;
    }

    private String normalizeForMatch(String text) {
        return text.toLowerCase().replaceAll("\\s+", " ");
    }

    private boolean containsVerbatim(String normalizedDocText, String quote) {
        if (quote == null || quote.isBlank()) {
            return false;
        }
        return normalizedDocText.contains(normalizeForMatch(quote));
    }

    private void saveInsight(Long documentId, User requester, String status, String resultJson) {
        AiInsight insight = new AiInsight();
        insight.setDocumentId(documentId);
        insight.setRequestedBy(requester.getUsername());
        insight.setStatus(status);
        insight.setResultJson(resultJson);
        insight.setCreatedAt(LocalDateTime.now());
        aiInsightRepository.save(insight);
    }

    private void requireOwnerOrAdmin(DocumentRecord document, User requester) {
        boolean isOwner = document.getUploadedBy().getId().equals(requester.getId());
        boolean isAdmin = requester.getRole() == Role.ADMIN;

        if (!isOwner && !isAdmin) {
            throw new AccessDeniedException("You do not have access to this document");
        }
    }

    private static class OpenRouterRequest {
        public String model;
        public List<Message> messages;

        public OpenRouterRequest(String model, String prompt) {
            this.model = model;
            this.messages = List.of(new Message("user", prompt));
        }

        static class Message {
            public String role;
            public String content;
            Message(String role, String content) {
                this.role = role;
                this.content = content;
            }
        }
    }

}