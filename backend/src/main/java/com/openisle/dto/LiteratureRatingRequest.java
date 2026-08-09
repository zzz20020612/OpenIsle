package com.openisle.dto;

import lombok.Data;

@Data
public class LiteratureRatingRequest {
  private Integer originalityScore;
  private Integer rigorScore;
  private Integer evidenceScore;
  private Integer significanceScore;
  private Integer reproducibilityScore;
  private Integer clarityScore;
  private Boolean readConfirmed;
  private String comment;
}
