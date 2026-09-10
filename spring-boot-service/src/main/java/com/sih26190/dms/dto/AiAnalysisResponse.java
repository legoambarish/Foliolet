package com.sih26190.dms.dto;

import java.time.LocalDateTime;
import java.util.List;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class AiAnalysisResponse {

    private Long documentId;
    private String summary;
    private List<KeyDate> keyDates;
    private List<KeyParty> keyParties;
    private List<FlaggedClause> flaggedClauses;
    private LocalDateTime analyzedAt;

    @Getter
    @Setter
    @NoArgsConstructor
    @AllArgsConstructor
    public static class KeyDate {
        private String date;
        private String context;
    }

    @Getter
    @Setter
    @NoArgsConstructor
    @AllArgsConstructor
    public static class KeyParty {
        private String name;
        private String context;
    }

    @Getter
    @Setter
    @NoArgsConstructor
    @AllArgsConstructor
    public static class FlaggedClause {
        private String quote;
        private String concern;
    }

}