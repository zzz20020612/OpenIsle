package com.openisle.dto;

import java.util.List;
import lombok.Data;

@Data
public class PaperAuthorRequest {
  private String displayName;
  private String givenName;
  private String middleName;
  private String familyName;
  private String email;
  private String orcid;
  private String authorRole;
  private String institutionName;
  private String country;
  private Boolean correspondingAuthor;
  private Boolean equalContribution;
  private List<String> contributionRoles;
  private List<PaperAffiliationRequest> affiliations;
}
