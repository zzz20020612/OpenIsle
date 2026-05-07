package com.openisle.dto;

import java.util.List;
import lombok.Data;

@Data
public class PaperAuthorRequest {
  private String displayName;
  private String email;
  private String orcid;
  private String institutionName;
  private String country;
  private Boolean correspondingAuthor;
  private Boolean equalContribution;
  private List<String> contributionRoles;
}
