package com.openisle.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

@Entity
@Getter
@Setter
@NoArgsConstructor
@Table(
  name = "paper_score_snapshots",
  indexes = {
    @Index(name = "idx_paper_score_snapshots_paper", columnList = "paper_id"),
    @Index(name = "idx_paper_score_snapshots_composite", columnList = "composite_score"),
  }
)
public class PaperScoreSnapshot {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @OneToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "paper_id", nullable = false, unique = true)
  private PaperProfile paper;

  @Column(name = "rating_count", nullable = false)
  private int ratingCount;

  @Column(name = "average_overall_score", nullable = false)
  private double averageOverallScore;

  @Column(name = "average_innovation_score", nullable = false)
  private double averageInnovationScore;

  @Column(name = "average_method_score", nullable = false)
  private double averageMethodScore;

  @Column(name = "average_impact_score", nullable = false)
  private double averageImpactScore;

  @Column(name = "composite_score", nullable = false)
  private double compositeScore;

  @CreationTimestamp
  @Column(name = "created_at", nullable = false, updatable = false)
  private LocalDateTime createdAt;

  @UpdateTimestamp
  @Column(name = "updated_at", nullable = false)
  private LocalDateTime updatedAt;
}
