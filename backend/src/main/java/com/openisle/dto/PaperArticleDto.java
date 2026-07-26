package com.openisle.dto;

import com.openisle.model.PaperArticleStatus;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import lombok.Data;

@Data
public class PaperArticleDto {
  private long version;
  private PaperArticleStatus status = PaperArticleStatus.NOT_STARTED;
  private LocalDateTime readyAt;
  private LocalDateTime updatedAt;
  private List<PaperArticleSectionDto> sections = new ArrayList<>();
}
