package com.openisle.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class PaperArticleIssueDto {
  private String sectionKey;
  private String blockKey;
  private String field;
  private String code;
  private String message;
}
