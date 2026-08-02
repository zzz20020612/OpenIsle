package com.openisle.dto;

import com.openisle.model.ExpertIdentityStatus;
import java.util.List;
import lombok.Data;

@Data
public class ExpertProfileDto {
  private Long id;
  private Long userId;
  private String displayName;
  private String email;
  private String orcid;
  private Long primaryInstitutionId;
  private String primaryInstitutionName;
  private String country;
  private ExpertIdentityStatus identityStatus;
  private int paperCount;
  private List<ExpertPaperDto> papers;
}
