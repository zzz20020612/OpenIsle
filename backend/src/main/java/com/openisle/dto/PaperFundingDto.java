package com.openisle.dto;

import lombok.Data;

@Data
public class PaperFundingDto {
  private Long id;
  private String funderName;
  private String grantId;
  private int displayOrder;
}
