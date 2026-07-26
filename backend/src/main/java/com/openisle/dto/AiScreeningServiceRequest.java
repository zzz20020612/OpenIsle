package com.openisle.dto;

import java.util.List;
import java.util.Map;
import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class AiScreeningServiceRequest {
  private Long paperId;
  private String manuscriptUrl;
  private String manuscriptFileName;
  private String title;
  private List<String> authors;
  private String subjectArea;
  private String paperType;
  private Map<String, String> declarations;
}
