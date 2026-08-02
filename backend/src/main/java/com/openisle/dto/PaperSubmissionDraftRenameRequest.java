package com.openisle.dto;

import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class PaperSubmissionDraftRenameRequest {

  @Size(max = 160, message = "Draft name must be 160 characters or fewer")
  private String displayName;
}
