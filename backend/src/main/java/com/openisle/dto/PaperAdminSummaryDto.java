package com.openisle.dto;

import com.openisle.model.PaperPublicationStatus;
import com.openisle.model.PaperScreeningStatus;
import com.openisle.model.PostStatus;
import java.time.LocalDateTime;
import java.util.List;
import lombok.Data;

@Data
public class PaperAdminSummaryDto {
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
  private String submitterUsername;
  private PostStatus postStatus;
  private boolean discussionClosed;
  private boolean pinned;
  private boolean rssExcluded;
  private LocalDateTime createdAt;
  private LocalDateTime publishedAt;
  private PaperScoreSnapshotDto scoreSnapshot;
  private AiScreeningDto screening;
}
