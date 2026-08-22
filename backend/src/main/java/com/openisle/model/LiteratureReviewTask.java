package com.openisle.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;

@Entity
@Getter
@Setter
@NoArgsConstructor
@Table(name = "literature_review_tasks", uniqueConstraints = @UniqueConstraint(name = "uk_literature_review_task_paper_reviewer", columnNames = {"literature_paper_id", "reviewer_id"}), indexes = {
  @Index(name = "idx_literature_review_task_reviewer_status", columnList = "reviewer_id,status")
})
public class LiteratureReviewTask {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @Column(name = "literature_paper_id", nullable = false)
  private Long literaturePaperId;

  @Column(nullable = false, length = 500)
  private String title;

  @Column(length = 500)
  private String authors;

  @Column(length = 255)
  private String journal;

  private Integer publicationYear;

  @ManyToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "reviewer_id", nullable = false)
  private User reviewer;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false, length = 20)
  private LiteratureReviewTaskStatus status;

  @Column(nullable = false)
  private boolean conflictDeclared;

  @Column(nullable = false)
  private LocalDateTime claimedAt;

  @Column(nullable = false)
  private LocalDateTime dueAt;

  private LocalDateTime completedAt;

  @Column(nullable = false)
  private int awardedPoints;

  @CreationTimestamp
  @Column(nullable = false, updatable = false)
  private LocalDateTime createdAt;
}
