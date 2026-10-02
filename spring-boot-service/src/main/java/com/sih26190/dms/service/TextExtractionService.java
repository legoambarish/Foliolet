package com.sih26190.dms.service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.springframework.stereotype.Service;

@Service
public class TextExtractionService {

    //staying within context window :D
    private static final int MAX_CHARS_FOR_LLM = 15000;

    public String extractText(Path filePath, String originalFileName) throws IOException {
        String lower = originalFileName == null ? "" : originalFileName.toLowerCase();

        String text = lower.endsWith(".pdf")
                ? extractFromPdf(filePath)
                : Files.readString(filePath); // plain-text fallback, useful for quick testing

        if (text.length() > MAX_CHARS_FOR_LLM) {
            text = text.substring(0, MAX_CHARS_FOR_LLM);
        }
        return text;
    }

    public String extractBytes(byte[] bytes, String filename) throws IOException {
        String lower=filename==null ? "" : filename.toLowerCase(java.util.Locale.ROOT);
        String text;
        if(lower.endsWith(".pdf")) {
            try(PDDocument doc=Loader.loadPDF(bytes)) { text=new PDFTextStripper().getText(doc); }
        } else if(lower.endsWith(".txt") || lower.endsWith(".csv")) {
            text=new String(bytes, java.nio.charset.StandardCharsets.UTF_8);
        } else return "";
        return text.substring(0,Math.min(text.length(),MAX_CHARS_FOR_LLM));
    }

    private String extractFromPdf(Path filePath) throws IOException {
        try (PDDocument document = Loader.loadPDF(filePath.toFile())) {
            return new PDFTextStripper().getText(document);
        }
    }

}