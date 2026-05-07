package com.openisle.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class PaperFileRecordDto {
  private String fileName;
  private String fileType;
  private Long fileSize;
  private String fileRole;
}
