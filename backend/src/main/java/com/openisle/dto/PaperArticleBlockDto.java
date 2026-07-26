package com.openisle.dto;

import java.util.ArrayList;
import java.util.List;
import lombok.Data;

@Data
public class PaperArticleBlockDto {
  private String key;
  private String type;
  private int displayOrder;
  private String text;
  private Long fileId;
  private String label;
  private String caption;
  private String altText;
  private String sourceNote;
  private String latex;
  private boolean numbered = true;
  private List<String> columns = new ArrayList<>();
  private List<List<String>> rows = new ArrayList<>();
  private String notes;
}
