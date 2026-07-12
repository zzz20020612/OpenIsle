package com.openisle.dto;

import com.openisle.model.PaperPublicationStatus;
import com.openisle.model.PaperScreeningStatus;
import lombok.Data;

@Data
public class PaperSubmissionResultDto {
  private Long paperId;
  private Long postId;
  private PaperPublicationStatus publicationStatus;
  private PaperScreeningStatus screeningStatus;
}
