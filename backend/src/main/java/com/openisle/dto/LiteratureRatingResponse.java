package com.openisle.dto;

import java.time.LocalDateTime;
import lombok.Data;

@Data
public class LiteratureRatingResponse {
  private Long ratingId;
  private Long literaturePaperId;
  private Long raterId;
  private String raterUsername;
  private int originalityScore;
  private int rigorScore;
  private int evidenceScore;
  private int significanceScore;
  private int reproducibilityScore;
  private int clarityScore;
  private String comment;
  private LocalDateTime updatedAt;
  private LiteratureScoreSnapshotDto scoreSnapshot;
}
