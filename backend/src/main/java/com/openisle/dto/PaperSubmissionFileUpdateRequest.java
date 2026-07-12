package com.openisle.dto;

import com.openisle.model.PaperFileRole;
import com.openisle.model.PaperFileVisibility;
import com.openisle.model.PaperUploadStatus;
import lombok.Data;

@Data
public class PaperSubmissionFileUpdateRequest {
  private String displayName;
  private PaperFileRole role;
  private String description;
  private PaperFileVisibility visibility;
  private PaperUploadStatus uploadStatus;
  private Integer sortOrder;
}
