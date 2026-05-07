package com.openisle.dto;

import lombok.Data;

@Data
public class PaperRankingDto {

  private int rank;
  private Long paperId;
  private Long postId;
  private String title;
  private String subjectArea;
  private int ratingCount;
  private double averageOverallScore;
  private double compositeScore;
}
