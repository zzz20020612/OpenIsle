package com.openisle.dto;

import java.time.LocalDateTime;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class LiteratureReviewTaskDto {
  private Long id;
  private Long literaturePaperId;
  private String title;
  private String authors;
  private String journal;
  private Integer year;
  private String status;
  private LocalDateTime claimedAt;
  private LocalDateTime dueAt;
  private LocalDateTime completedAt;
  private Integer awardedPoints;
}
