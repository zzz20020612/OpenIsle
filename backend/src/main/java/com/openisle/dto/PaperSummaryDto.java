package com.openisle.dto;

import com.openisle.model.PaperPublicationStatus;
import com.openisle.model.PaperScreeningStatus;
import java.time.LocalDateTime;
import java.util.List;
import lombok.Data;

@Data
public class PaperSummaryDto {
  private Long id;
  private Long postId;
  private String title;
  private String abstractText;
  private List<String> keywords;
  private String subjectArea;
  private String paperType;
  private PaperPublicationStatus publicationStatus;
  private PaperScreeningStatus screeningStatus;
  private String primaryInstitutionName;
  private List<PaperAuthorDto> authors;
  private LocalDateTime publishedAt;
  private boolean featured;
  private boolean rssExcluded;
  private long commentCount;
  private long views;
  private PaperScoreSnapshotDto scoreSnapshot;
}
