package com.openisle.dto;

import lombok.Data;

@Data
public class PaperAffiliationRequest {
  private String organizationName;
  private String department;
  private String addressLine1;
  private String addressLine2;
  private String country;
  private String region;
  private String city;
  private String postalCode;
  private Boolean primaryAffiliation;
}
