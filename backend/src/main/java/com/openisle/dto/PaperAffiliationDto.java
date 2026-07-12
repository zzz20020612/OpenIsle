package com.openisle.dto;

import lombok.Data;

@Data
public class PaperAffiliationDto {
  private Long id;
  private String organizationName;
  private String department;
  private String country;
  private String region;
  private String city;
  private boolean primaryAffiliation;
  private int displayOrder;
}
