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
  name = "paper_ratings",
  uniqueConstraints = {
    @UniqueConstraint(name = "uk_paper_ratings_paper_rater", columnNames = { "paper_id", "rater_id" }),
  },
  indexes = {
    @Index(name = "idx_paper_ratings_paper", columnList = "paper_id"),
    @Index(name = "idx_paper_ratings_rater", columnList = "rater_id"),
  }
)
public class PaperRating {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @ManyToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "paper_id", nullable = false)
  private PaperProfile paper;

  @ManyToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "rater_id", nullable = false)
  private User rater;

  @Column(name = "overall_score", nullable = false)
  private int overallScore;

  @Column(name = "innovation_score", nullable = false)
  private int innovationScore;

  @Column(name = "method_score", nullable = false)
  private int methodScore;

  @Column(name = "impact_score", nullable = false)
  private int impactScore;

  @Column(columnDefinition = "TEXT")
  private String comment;

  @CreationTimestamp
  @Column(name = "created_at", nullable = false, updatable = false)
  private LocalDateTime createdAt;

  @UpdateTimestamp
  @Column(name = "updated_at", nullable = false)
  private LocalDateTime updatedAt;
}
