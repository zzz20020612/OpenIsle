package com.openisle.dto;

import lombok.Data;

@Data
public class PaperSubmissionSubmitRequest {
  private long version;
  private String idempotencyKey;
  private Boolean metadataMatchesManuscript;
  private Boolean correspondingAuthorInformationConfirmed;
  private Boolean publicDisplayConfirmed;
}
