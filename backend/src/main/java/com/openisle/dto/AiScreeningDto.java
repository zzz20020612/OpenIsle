package com.openisle.dto;

import com.openisle.model.PaperScreeningStatus;
import java.time.LocalDateTime;
import lombok.Data;

@Data
public class AiScreeningDto {
  private PaperScreeningStatus status;
  private String riskLevel;
  private String detectedSubjectArea;
  private String detectedPaperType;
  private String summary;
  private String issuesJson;
  private LocalDateTime screenedAt;
}
