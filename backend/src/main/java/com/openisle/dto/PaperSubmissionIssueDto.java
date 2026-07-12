package com.openisle.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class PaperSubmissionIssueDto {
  private String section;
  private String field;
  private String code;
  private String message;
}
