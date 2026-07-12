package com.openisle.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.openisle.model.PaperFileVisibility;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
public class PaperFileRecordDto {
  private Long id;
  private String fileName;
  private String displayName;
  private String fileType;
  private Long fileSize;
  private String fileRole;
  private String description;
  private PaperFileVisibility visibility;
  private boolean previewable;
  private boolean tocGraphic;
  private long viewCount;
  private long downloadCount;

  @JsonProperty(access = JsonProperty.Access.WRITE_ONLY)
  private String url;

  @JsonProperty(access = JsonProperty.Access.WRITE_ONLY)
  private String key;

  public PaperFileRecordDto(String fileName, String fileType, Long fileSize, String fileRole) {
    this.fileName = fileName;
    this.fileType = fileType;
    this.fileSize = fileSize;
    this.fileRole = fileRole;
  }
}
