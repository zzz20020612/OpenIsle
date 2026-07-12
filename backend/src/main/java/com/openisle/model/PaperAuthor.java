package com.openisle.model;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Getter
@Setter
@NoArgsConstructor
@Table(
  name = "paper_authors",
  indexes = {
    @Index(name = "idx_paper_authors_paper", columnList = "paper_id"),
    @Index(name = "idx_paper_authors_name", columnList = "display_name")
  }
)
public class PaperAuthor {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @ManyToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "paper_id", nullable = false)
  private PaperProfile paper;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "user_id")
  private User user;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "expert_profile_id")
  private ExpertProfile expertProfile;

  @Column(name = "display_name", nullable = false)
  private String displayName;

  @Column(name = "given_name")
  private String givenName;

  @Column(name = "middle_name")
  private String middleName;

  @Column(name = "family_name")
  private String familyName;

  @Column(name = "author_role")
  private String authorRole;

  @Column
  private String email;

  @Column
  private String orcid;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "institution_id")
  private Institution institution;

  @Column
  private String country;

  @Column(name = "author_order", nullable = false)
  private int authorOrder;

  @Column(name = "corresponding_author", nullable = false)
  private boolean correspondingAuthor = false;

  @Column(name = "equal_contribution", nullable = false)
  private boolean equalContribution = false;

  @Column(name = "contribution_roles", columnDefinition = "TEXT")
  private String contributionRoles;

  @Enumerated(EnumType.STRING)
  @Column(name = "identity_status", nullable = false)
  private ExpertIdentityStatus identityStatus = ExpertIdentityStatus.UNMATCHED;
}
