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
  private List<PaperFundingRequest> funding;
  private Boolean noFundingReceived;
  private String preprintStatement;
  private String aiUseDisclosure;
  private Boolean allAuthorsConsent;
  private Boolean originalityConfirmed;
  private Boolean rightsConfirmed;
  private Boolean correspondingAuthorContactConfirmed;
  private String privateComments;
}
