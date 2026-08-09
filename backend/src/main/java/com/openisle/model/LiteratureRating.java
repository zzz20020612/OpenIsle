package com.openisle.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
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
  name = "literature_ratings",
  uniqueConstraints = {
    @UniqueConstraint(
      name = "uk_literature_ratings_paper_rater",
      columnNames = { "literature_paper_id", "rater_id" }
    ),
  },
  indexes = {
    @Index(name = "idx_literature_ratings_paper", columnList = "literature_paper_id"),
    @Index(name = "idx_literature_ratings_rater", columnList = "rater_id"),
  }
)
public class LiteratureRating {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @Column(name = "literature_paper_id", nullable = false)
  private Long literaturePaperId;

  @ManyToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "rater_id", nullable = false)
  private User rater;

  @Column(name = "originality_score", nullable = false)
  private int originalityScore;

  @Column(name = "rigor_score", nullable = false)
  private int rigorScore;

  @Column(name = "evidence_score", nullable = false)
  private int evidenceScore;

  @Column(name = "significance_score", nullable = false)
  private int significanceScore;

  @Column(name = "reproducibility_score", nullable = false)
  private int reproducibilityScore;

  @Column(name = "clarity_score", nullable = false)
  private int clarityScore;

  @Column(name = "read_confirmed", nullable = false)
  private boolean readConfirmed;

  @Column(nullable = false, length = 500)
  private String comment;

  @CreationTimestamp
  @Column(name = "created_at", nullable = false, updatable = false)
  private LocalDateTime createdAt;

  @UpdateTimestamp
  @Column(name = "updated_at", nullable = false)
  private LocalDateTime updatedAt;
}
