package com.openisle.dto;

import java.util.List;
import lombok.Data;

@Data
public class PaperSubmitRequest {
  private Long categoryId;
  private List<Long> tagIds;
  private String title;
  private String abstractText;
  private List<String> keywords;
  private List<String> references;
  private List<PaperFileRecordDto> manuscriptFiles;
  private List<PaperFileRecordDto> supplementaryFiles;
  private String subjectArea;
  private String paperType;
  private String content;
  private String primaryInstitutionName;
  private String fundingStatement;
  private String conflictOfInterest;
  private String dataAvailability;
  private String ethicsStatement;
  private List<PaperAuthorRequest> authors;
}
