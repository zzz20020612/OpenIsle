package com.openisle.dto;

import com.openisle.model.ExpertIdentityStatus;
import lombok.Data;

@Data
public class PaperAuthorDto {
  private Long id;
  private int authorOrder;
  private String displayName;
  private Long institutionId;
  private String institution;
  private String country;
  private boolean correspondingAuthor;
  private boolean equalContribution;
  private ExpertIdentityStatus identityStatus;
  private Long expertProfileId;
  private Long userId;
}
