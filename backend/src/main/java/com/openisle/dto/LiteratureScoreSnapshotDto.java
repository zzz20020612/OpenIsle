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
  private Double compositeScore;
  private double unshrunkCompositeScore;
  private double effectiveSampleSize;
  private int institutionCount;
  private double largestInstitutionShare;
  private String rankingStatus;
  private boolean rankingEligible;
  private String ruleVersion;
}
