package com.openisle.dto;

import java.util.List;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class PaperSubmissionValidationDto {
  private boolean valid;
  private List<PaperSubmissionIssueDto> issues;
}
