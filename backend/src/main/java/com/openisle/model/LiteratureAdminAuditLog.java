package com.openisle.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;

@Entity
@Getter
@Setter
@NoArgsConstructor
@Table(name = "literature_admin_audit_logs", indexes = {
  @Index(name = "idx_literature_audit_created", columnList = "created_at"),
  @Index(name = "idx_literature_audit_actor", columnList = "actor_username")
})
public class LiteratureAdminAuditLog {
  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @Column(name = "actor_username", nullable = false, length = 100)
  private String actorUsername;

  @Column(nullable = false, length = 12)
  private String method;

  @Column(nullable = false, length = 160)
  private String operation;

  @Column(name = "request_summary", columnDefinition = "TEXT")
  private String requestSummary;

  @Column(nullable = false)
  private boolean successful;

  @Column(name = "upstream_status", nullable = false)
  private int upstreamStatus;

  @Column(name = "remote_address", length = 80)
  private String remoteAddress;

  @CreationTimestamp
  @Column(name = "created_at", nullable = false, updatable = false)
  private LocalDateTime createdAt;
}
