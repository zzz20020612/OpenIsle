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
  name = "expert_profiles",
  indexes = {
    @Index(name = "idx_expert_profiles_orcid", columnList = "orcid"),
    @Index(name = "idx_expert_profiles_email", columnList = "email"),
    @Index(name = "idx_expert_profiles_name", columnList = "display_name")
  }
)
public class ExpertProfile {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "user_id")
  private User user;

  @Column(name = "display_name", nullable = false)
  private String displayName;

  @Column
  private String email;

  @Column
  private String orcid;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "primary_institution_id")
  private Institution primaryInstitution;

  @Column
  private String country;

  @Enumerated(EnumType.STRING)
  @Column(name = "identity_status", nullable = false)
  private ExpertIdentityStatus identityStatus = ExpertIdentityStatus.UNMATCHED;

  @CreationTimestamp
  @Column(nullable = false, updatable = false)
  private LocalDateTime createdAt;

  @UpdateTimestamp
  @Column(nullable = false)
  private LocalDateTime updatedAt;
}
