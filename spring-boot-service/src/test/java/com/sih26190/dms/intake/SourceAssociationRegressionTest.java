package com.sih26190.dms.intake;

import com.sih26190.dms.foli.CitationVerifier;
import com.sih26190.dms.foli.FoliLocalModel;
import com.sih26190.dms.selective.ClaimCanonicalizer;
import java.util.List;
import org.junit.jupiter.api.Test;
import static com.sih26190.dms.foli.FoliData.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.mock;

/** Adversarial cases discovered independently of the historical OCR corpus. */
class SourceAssociationRegressionTest {
    private final FactSuggestions facts = new FactSuggestions(
            new ClaimCanonicalizer(), new CitationVerifier(), mock(FoliLocalModel.class));
    private static final String HASH = "e".repeat(64);

    private Snapshot snapshot(String text, String format, List<Layer> layers) {
        var document = new Document("wallet:0x" + HASH, "Fictional regression", "fixture." + format,
                format, "DRAFT", "1", true);
        return new Snapshot(document, HASH, List.of(new Page(1, text,
                layers.size() > 1 ? "MIXED_OCR" : "TEXT", null, 1, 1, 0,
                List.of(), List.of(), layers)), null);
    }

    private FactSuggestions.Result suggest(Snapshot source) {
        return facts.suggest(source, ignored -> {});
    }

    private Snapshot mixed(String otherLabel, int ocrX, int ocrY, int rotation) {
        String nativeText = "Math: 91";
        String text = nativeText + "\n" + otherLabel + ": 91";
        int offset = nativeText.length() + 1;
        var nativeLayer = new Layer("native", "NATIVE", 0, 1000, 1000,
                List.of(new Word("Math:", 0, 5, 20, 20, 50, 20, 100),
                        new Word("91", 6, 8, 80, 20, 20, 20, 100)), List.of());
        var ocrLayer = new Layer("ocr", "OCR", rotation, 1000, 1000,
                List.of(new Word(otherLabel + ":", offset, offset + otherLabel.length() + 1,
                                ocrX, ocrY, 50, 20, 99),
                        new Word("91", offset + otherLabel.length() + 2, text.length(),
                                ocrX + 60, ocrY, 20, 20, 99)), List.of());
        return snapshot(text, "pdf", List.of(nativeLayer, ocrLayer));
    }

    @Test void candidateNameAndIdentifierAreNotDates() {
        var result = suggest(snapshot("Candidate Name: Fictional Student\nCandidate ID: 001234\n", "txt", List.of()));
        assertEquals(2, result.fields().size());
        for (var field : result.fields()) {
            assertEquals("string", field.type());
            assertEquals("SUPPORTED", field.support().quality(), field.label() + ": " + field.support().reasons());
        }
    }

    @Test void explicitDateLabelsStillUseStrictDateNormalization() {
        var result = suggest(snapshot("Issue Date: 14 July 2026\nDate of Birth: 2004-07-14\n", "txt", List.of()));
        assertEquals(2, result.fields().size());
        assertTrue(result.fields().stream().allMatch(f -> f.type().equals("date")));
        assertTrue(result.fields().stream().anyMatch(f -> f.value().equals("2026-07-14")));
    }

    @Test void sameValueElsewhereOnPageCannotCorroborateNativeField() {
        var field = suggest(mixed("Math", 420, 620, 0)).fields().get(0);
        assertEquals("REVIEW_REQUIRED", field.support().quality());
        assertTrue(field.support().reasons().contains("RENDERED_VALUE_NOT_CORROBORATED"));
        assertNotEquals("Embedded text corroborated by OCR", field.citation().provenance());
    }

    @Test void matchingPositionAndLabelStillCorroborateNativeField() {
        var field = suggest(mixed("Math", 20, 20, 0)).fields().get(0);
        assertEquals("SUPPORTED", field.support().quality());
        assertEquals("Embedded text corroborated by OCR", field.citation().provenance());
    }

    @Test void identicalValueWithDifferentRenderedLabelDoesNotEarnCorroboration() {
        var field = suggest(mixed("Physics", 20, 20, 0)).fields().get(0);
        assertTrue(field.support().reasons().contains("LABEL_READINGS_DISAGREE"));
        assertTrue(field.support().reasons().contains("RENDERED_VALUE_NOT_CORROBORATED"));
        assertNotEquals("Embedded text corroborated by OCR", field.citation().provenance());
    }

    @Test void differentRotationFramesDoNotEarnCorroboration() {
        var field = suggest(mixed("Math", 20, 20, 90)).fields().get(0);
        assertEquals("REVIEW_REQUIRED", field.support().quality());
        assertTrue(field.support().reasons().contains("RENDERED_VALUE_NOT_CORROBORATED"));
    }

    @Test void offPageGeometryCannotBecomeInspectableSupportedEvidence() {
        for (int[] box : new int[][]{{-200, 20, 80, 20}, {20, -200, 80, 20},
                {990, 20, 80, 20}, {20, 990, 80, 20}, {Integer.MAX_VALUE, 20, 80, 20}}) {
            var layer = new Layer("native", "NATIVE", 0, 1000, 1000,
                    List.of(new Word("Math: 91", 0, 8, box[0], box[1], box[2], box[3], 100)), List.of());
            assertTrue(suggest(snapshot("Math: 91", "pdf", List.of(layer))).fields().isEmpty(),
                    "Off-page or overflowing source rectangle must be rejected");
        }
    }

    @Test void confidenceOutsideDocumentedScaleCannotBecomeEvidence() {
        for (double confidence : new double[]{-0.01, 100.01, Double.NaN, Double.POSITIVE_INFINITY}) {
            var layer = new Layer("native", "NATIVE", 0, 1000, 1000,
                    List.of(new Word("Math: 91", 0, 8, 20, 20, 80, 20, confidence)), List.of());
            assertTrue(suggest(snapshot("Math: 91", "pdf", List.of(layer))).fields().isEmpty(),
                    "Invalid confidence: " + confidence);
        }
    }
}
