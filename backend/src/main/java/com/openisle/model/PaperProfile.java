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
  name = "paper_profiles",
  indexes = {
    @Index(name = "idx_paper_profiles_status", columnList = "publication_status"),
    @Index(name = "idx_paper_profiles_subject", columnList = "subject_area"),
    @Index(name = "idx_paper_profiles_published_at", columnList = "published_at")
  }
)
public class PaperProfile {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @OneToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "post_id", nullable = false, unique = true)
  private Post post;

  @Column(nullable = false)
  private String title;

  @Column(name = "abstract_text", nullable = false, columnDefinition = "TEXT")
  private String abstractText;

  @Column(columnDefinition = "TEXT")
  private String keywords;

  @Column(name = "references_text", columnDefinition = "TEXT")
  private String referencesText;

  @Column(name = "manuscript_files", columnDefinition = "TEXT")
  private String manuscriptFiles;

  @Column(name = "supplementary_files", columnDefinition = "TEXT")
  private String supplementaryFiles;

  @Column(name = "subject_area", nullable = false)
  private String subjectArea;

  @Column(name = "paper_type")
  private String paperType;

  @Column(name = "funding_statement", columnDefinition = "TEXT")
  private String fundingStatement;

  @Column(name = "conflict_of_interest", columnDefinition = "TEXT")
  private String conflictOfInterest;

  @Column(name = "data_availability", columnDefinition = "TEXT")
  private String dataAvailability;

  @Column(name = "ethics_statement", columnDefinition = "TEXT")
  private String ethicsStatement;

  @Column(name = "preprint_statement", columnDefinition = "TEXT")
  private String preprintStatement;

  @Column(name = "ai_use_disclosure", columnDefinition = "TEXT")
  private String aiUseDisclosure;

  @Column(name = "private_comments", columnDefinition = "TEXT")
  private String privateComments;

  @Column(name = "all_authors_consent", nullable = false)
  private boolean allAuthorsConsent;

  @Column(name = "originality_confirmed", nullable = false)
  private boolean originalityConfirmed;

  @Column(name = "rights_confirmed", nullable = false)
  private boolean rightsConfirmed;

  @Column(name = "corresponding_author_contact_confirmed", nullable = false)
  private boolean correspondingAuthorContactConfirmed;

  @Column(name = "corresponding_author_contact_confirmed_at")
  private LocalDateTime correspondingAuthorContactConfirmedAt;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "corresponding_author_contact_confirmed_by")
  private User correspondingAuthorContactConfirmedBy;

  @Enumerated(EnumType.STRING)
  @Column(name = "publication_status", nullable = false)
  private PaperPublicationStatus publicationStatus = PaperPublicationStatus.DRAFT;

  @Enumerated(EnumType.STRING)
  @Column(name = "screening_status", nullable = false)
  private PaperScreeningStatus screeningStatus = PaperScreeningStatus.NOT_SCREENED;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "primary_institution_id")
  private Institution primaryInstitution;

  @ManyToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "created_by")
  private User createdBy;

  @Column(name = "published_at")
  private LocalDateTime publishedAt;

  @CreationTimestamp
  @Column(nullable = false, updatable = false)
  private LocalDateTime createdAt;

  @UpdateTimestamp
  @Column(nullable = false)
  private LocalDateTime updatedAt;
}
