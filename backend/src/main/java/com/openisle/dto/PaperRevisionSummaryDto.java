package com.openisle.dto;

import com.openisle.model.PaperPublicationStatus;
import com.openisle.model.PaperScreeningStatus;
import java.time.LocalDateTime;
import lombok.Data;

@Data
public class PaperRevisionSummaryDto {
  private Long id;
  private int revisionNumber;
  private String title;
  private PaperPublicationStatus publicationStatus;
  private PaperScreeningStatus screeningStatus;
  private LocalDateTime submittedAt;
  private boolean latest;
}
