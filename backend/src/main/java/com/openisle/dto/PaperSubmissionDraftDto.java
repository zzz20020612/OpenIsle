package com.openisle.dto;

import com.openisle.model.PaperSubmissionDraftStatus;
import java.time.LocalDateTime;
import java.util.List;
import lombok.Data;

@Data
public class PaperSubmissionDraftDto {
  private Long id;
  private long version;
  private String manuscriptType;
  private String currentSection;
  private PaperSubmissionDraftStatus status;
  private PaperSubmitRequest formData;
  private List<PaperSubmissionFileDto> files;
  private Long submittedPaperId;
  private LocalDateTime createdAt;
  private LocalDateTime updatedAt;
}
