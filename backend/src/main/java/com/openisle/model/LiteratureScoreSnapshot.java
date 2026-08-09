package com.openisle.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.UpdateTimestamp;

@Entity
@Getter
@Setter
@NoArgsConstructor
@Table(name = "literature_score_snapshots")
public class LiteratureScoreSnapshot {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @Column(name = "literature_paper_id", nullable = false, unique = true)
  private Long literaturePaperId;

  @Column(name = "rating_count", nullable = false)
  private int ratingCount;

  @Column(name = "average_originality_score", nullable = false)
  private double averageOriginalityScore;

  @Column(name = "average_rigor_score", nullable = false)
  private double averageRigorScore;

  @Column(name = "average_evidence_score", nullable = false)
  private double averageEvidenceScore;

  @Column(name = "average_significance_score", nullable = false)
  private double averageSignificanceScore;

  @Column(name = "average_reproducibility_score", nullable = false)
  private double averageReproducibilityScore;

  @Column(name = "average_clarity_score", nullable = false)
  private double averageClarityScore;

  @Column(name = "composite_score", nullable = false)
  private double compositeScore;

  @UpdateTimestamp
  @Column(name = "calculated_at", nullable = false)
  private LocalDateTime calculatedAt;
}
