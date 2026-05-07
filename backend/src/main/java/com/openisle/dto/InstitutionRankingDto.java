package com.openisle.dto;

import lombok.Data;

@Data
public class InstitutionRankingDto {

  private int rank;
  private String institutionName;
  private int paperCount;
  private int totalRatingCount;
  private double averageCompositeScore;
}
