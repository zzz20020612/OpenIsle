package com.openisle.dto;

import java.util.ArrayList;
import java.util.List;
import lombok.Data;

@Data
public class LiteraturePaperRankingDto {
  private int rank;
  private Long literaturePaperId;
  private String title;
  private List<String> authors = new ArrayList<>();
  private String journal;
  private Integer year;
  private int ratingCount;
  private Double compositeScore;
  private LiteratureScoreSnapshotDto scoreSnapshot;
}
