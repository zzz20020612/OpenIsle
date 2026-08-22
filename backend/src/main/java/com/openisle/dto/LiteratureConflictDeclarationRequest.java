package com.openisle.dto;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class LiteratureConflictDeclarationRequest {
  private Boolean authorOrCoauthor;
  private Boolean sameInstitution;
  private Boolean recentCollaborator;
  private Boolean advisorOrStudent;
  private Boolean otherDirectConflict;
}
