package com.openisle.dto;

import java.util.List;
import lombok.Data;

@Data
public class PaperDetailDto extends PaperSummaryDto {
  private List<String> keywords;
  private List<String> references;
  private String content;
  private List<String> authorInstitutions;
  private String fundingStatement;
  private String conflictOfInterest;
  private String dataAvailability;
  private String ethicsStatement;
  private String preprintStatement;
  private String aiUseDisclosure;
  private List<PaperFundingDto> funding;
  private List<PaperFileRecordDto> manuscriptFiles;
  private List<PaperFileRecordDto> supplementaryFiles;
  private PaperFileRecordDto tocGraphic;
  private AiScreeningDto screening;
  private boolean subscribed;
}
