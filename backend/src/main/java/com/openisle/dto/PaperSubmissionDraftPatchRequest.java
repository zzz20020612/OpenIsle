package com.openisle.dto;

import lombok.Data;

@Data
public class PaperSubmissionDraftPatchRequest {
  private long version;
  private String currentSection;
  private PaperSubmitRequest formData;
}
