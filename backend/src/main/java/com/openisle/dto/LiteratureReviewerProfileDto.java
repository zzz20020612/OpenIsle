package com.openisle.dto;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class LiteratureReviewerProfileDto {
  private int points;
  private int acceptedTasks;
  private int completedTasks;
  private int onTimeTasks;
  private double onTimeRate;
  private double creditScore;
  private String level;
  private boolean eligible;
}
