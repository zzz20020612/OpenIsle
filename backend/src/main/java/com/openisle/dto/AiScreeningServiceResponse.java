package com.openisle.dto;

import java.util.List;
import java.util.Map;
import lombok.Data;

@Data
public class AiScreeningServiceResponse {
  private Long paperId;
  private String verdict;
  private String status;
  private String riskLevel;
  private String summary;
  private List<Map<String, Object>> dimensions;
  private List<String> skippedDimensions;
  private String reportMarkdown;
  private Map<String, Object> rawResult;
}
