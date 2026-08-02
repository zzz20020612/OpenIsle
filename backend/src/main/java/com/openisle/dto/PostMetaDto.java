package com.openisle.dto;

import com.openisle.model.PostType;
import java.time.LocalDateTime;
import java.util.List;
import lombok.Data;

/** Lightweight post metadata used in user profile lists. */
@Data
public class PostMetaDto {

  private Long id;
  private Long paperId;
  private PostType type;
  private String title;
  private String snippet;
  private LocalDateTime createdAt;
  private CategoryDto category;
  private List<TagDto> tags;
  private long views;
  private long commentCount;
}
