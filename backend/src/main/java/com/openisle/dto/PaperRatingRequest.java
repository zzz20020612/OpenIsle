package com.openisle.dto;

import lombok.Data;

@Data
public class PaperRatingRequest {

  private Integer overallScore;
  private Integer innovationScore;
  private Integer methodScore;
  private Integer impactScore;
  private String comment;
}
