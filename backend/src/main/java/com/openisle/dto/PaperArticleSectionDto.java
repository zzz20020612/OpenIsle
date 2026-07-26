package com.openisle.dto;

import java.util.ArrayList;
import java.util.List;
import lombok.Data;

@Data
public class PaperArticleSectionDto {
  private String key;
  private String parentKey;
  private String heading;
  private int level = 1;
  private int displayOrder;
  private List<PaperArticleBlockDto> blocks = new ArrayList<>();
}
