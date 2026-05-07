package com.openisle.dto;

import java.time.LocalDateTime;
import lombok.Data;

@Data
public class PaperRatingResponse {

  private Long ratingId;
  private Long paperId;
  private Long raterId;
  private int overallScore;
  private int innovationScore;
  private int methodScore;
  private int impactScore;
  private String comment;
  private LocalDateTime updatedAt;
  private PaperScoreSnapshotDto scoreSnapshot;
}
