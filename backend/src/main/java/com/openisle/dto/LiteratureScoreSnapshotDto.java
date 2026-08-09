package com.openisle.dto;

import lombok.Data;

@Data
public class LiteratureScoreSnapshotDto {
  private int ratingCount;
  private double averageOriginalityScore;
  private double averageRigorScore;
  private double averageEvidenceScore;
  private double averageSignificanceScore;
  private double averageReproducibilityScore;
  private double averageClarityScore;
  private double compositeScore;
}
