package com.openisle.dto;

import com.openisle.model.PaperFileRole;
import com.openisle.model.PaperFileVisibility;
import com.openisle.model.PaperUploadStatus;
import java.time.LocalDateTime;
import lombok.Data;

@Data
public class PaperSubmissionFileDto {
  private Long id;
  private String originalFileName;
  private String displayName;
  private String contentType;
  private long fileSize;
  private PaperFileRole role;
  private String description;
  private PaperFileVisibility visibility;
  private PaperUploadStatus uploadStatus;
  private int sortOrder;
  private LocalDateTime createdAt;
  private LocalDateTime updatedAt;
}
