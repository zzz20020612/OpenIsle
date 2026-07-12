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
  name = "paper_files",
  indexes = {
    @Index(name = "idx_paper_files_paper_order", columnList = "paper_id,sort_order,id"),
    @Index(name = "idx_paper_files_paper_role", columnList = "paper_id,role")
  }
)
public class PaperFile {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  @Column(name = "id")
  private Long id;

  @ManyToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "paper_id", nullable = false)
  private PaperProfile paper;

  @Column(name = "original_file_name", nullable = false)
  private String originalFileName;

  @Column(name = "display_name", nullable = false)
  private String displayName;

  @Column(name = "content_type", nullable = false)
  private String contentType;

  @Column(name = "file_size", nullable = false)
  private long fileSize;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false)
  private PaperFileRole role;

  @Column(columnDefinition = "TEXT")
  private String description;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false)
  private PaperFileVisibility visibility = PaperFileVisibility.PRIVATE;

  @Column(name = "storage_key", nullable = false)
  private String storageKey;

  @Enumerated(EnumType.STRING)
  @Column(name = "upload_status", nullable = false)
  private PaperUploadStatus uploadStatus = PaperUploadStatus.UPLOADED;

  @Column(name = "sort_order", nullable = false)
  private int sortOrder;

  @Column(name = "view_count", nullable = false)
  private long viewCount;

  @Column(name = "download_count", nullable = false)
  private long downloadCount;

  @CreationTimestamp
  @Column(name = "created_at", nullable = false, updatable = false)
  private LocalDateTime createdAt;

  @UpdateTimestamp
  @Column(name = "updated_at", nullable = false)
  private LocalDateTime updatedAt;
}
