package com.openisle.dto;

import java.time.LocalDateTime;
import java.util.Map;
import lombok.Data;

@Data
public class PaperSubmissionFilePresignResponse {
  private Long fileId;
  private String uploadUrl;
  private Map<String, String> uploadHeaders;
  private LocalDateTime expiresAt;
  private PaperSubmissionFileDto file;
}
