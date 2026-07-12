package com.openisle.model;

import jakarta.persistence.*;
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
  name = "paper_submission_drafts",
  indexes = {
    @Index(
      name = "idx_paper_submission_drafts_owner_status",
      columnList = "owner_id,status,updated_at"
    )
  }
)
public class PaperSubmissionDraft {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  @Column(name = "id")
  private Long id;

  @ManyToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "owner_id", nullable = false)
  private User owner;

  @Column(name = "manuscript_type")
  private String manuscriptType;

  @Column(name = "form_data_json", nullable = false, columnDefinition = "LONGTEXT")
  private String formDataJson;

  @Column(name = "current_section")
  private String currentSection;

  @Enumerated(EnumType.STRING)
  @Column(name = "status", nullable = false)
  private PaperSubmissionDraftStatus status = PaperSubmissionDraftStatus.IN_PROGRESS;

  @OneToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "submitted_paper_id", unique = true)
  private PaperProfile submittedPaper;

  @Column(name = "idempotency_key", unique = true)
  private String idempotencyKey;

  @Version
  @Column(nullable = false)
  private long version;

  @CreationTimestamp
  @Column(name = "created_at", nullable = false, updatable = false)
  private LocalDateTime createdAt;

  @UpdateTimestamp
  @Column(name = "updated_at", nullable = false)
  private LocalDateTime updatedAt;
}
