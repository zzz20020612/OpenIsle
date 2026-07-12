package com.openisle.dto;

import com.openisle.model.ExpertIdentityStatus;
import java.util.List;
import lombok.Data;

@Data
public class PaperAuthorDto {
  private Long id;
  private int authorOrder;
  private String displayName;
  private String givenName;
  private String middleName;
  private String familyName;
  private String email;
  private String orcid;
  private String authorRole;
  private Long institutionId;
  private String institution;
  private String country;
  private boolean correspondingAuthor;
  private boolean equalContribution;
  private List<String> contributionRoles;
  private List<PaperAffiliationDto> affiliations;
  private ExpertIdentityStatus identityStatus;
  private Long expertProfileId;
  private Long userId;
}
