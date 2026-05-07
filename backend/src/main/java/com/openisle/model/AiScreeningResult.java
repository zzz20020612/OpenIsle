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
@Table(name = "ai_screening_results")
public class AiScreeningResult {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @ManyToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "paper_id", nullable = false)
  private PaperProfile paper;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false)
  private PaperScreeningStatus status;

  @Column(name = "risk_level", nullable = false)
  private String riskLevel;

  @Column(name = "detected_subject_area")
  private String detectedSubjectArea;

  @Column(name = "detected_paper_type")
  private String detectedPaperType;

  @Column(columnDefinition = "TEXT")
  private String summary;

  @Column(name = "issues_json", columnDefinition = "TEXT")
  private String issuesJson;

  @Column(name = "raw_response_json", columnDefinition = "TEXT")
  private String rawResponseJson;

  @CreationTimestamp
  @Column(name = "screened_at", nullable = false, updatable = false)
  private LocalDateTime screenedAt;
}
