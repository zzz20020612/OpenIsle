package com.openisle.dto;

import java.time.LocalDateTime;
import lombok.Data;

@Data
public class ExpertPaperDto {
  private Long paperId;
  private Long postId;
  private String title;
  private String subjectArea;
  private String authorRole;
  private Integer authorOrder;
  private boolean correspondingAuthor;
  private boolean equalContribution;
  private LocalDateTime publishedAt;
  private PaperScoreSnapshotDto scoreSnapshot;
}
