package com.openisle.dto;

import lombok.Data;

@Data
public class PaperScoreSnapshotDto {

  private int ratingCount;
  private double averageOverallScore;
  private double averageInnovationScore;
  private double averageMethodScore;
  private double averageImpactScore;
  private double compositeScore;
}
