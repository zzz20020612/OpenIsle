package com.openisle.dto;

import java.util.ArrayList;
import java.util.List;
import lombok.Data;

@Data
public class PaperArticleValidationDto {
  private boolean valid;
  private List<PaperArticleIssueDto> issues = new ArrayList<>();
}
