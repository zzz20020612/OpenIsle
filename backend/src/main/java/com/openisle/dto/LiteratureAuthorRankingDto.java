package com.openisle.dto;

import lombok.Data;

@Data
public class LiteratureAuthorRankingDto {
  private int rank;
  private String authorName;
  private int paperCount;
  private int totalRatingCount;
  private double averageCompositeScore;
}
