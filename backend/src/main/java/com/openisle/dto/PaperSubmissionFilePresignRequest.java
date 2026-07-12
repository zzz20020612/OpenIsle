package com.openisle.dto;

import com.openisle.model.PaperFileRole;
import com.openisle.model.PaperFileVisibility;
import lombok.Data;

@Data
public class PaperSubmissionFilePresignRequest {
  private String fileName;
  private String displayName;
  private String contentType;
  private long fileSize;
  private PaperFileRole role;
  private String description;
  private PaperFileVisibility visibility;
}
