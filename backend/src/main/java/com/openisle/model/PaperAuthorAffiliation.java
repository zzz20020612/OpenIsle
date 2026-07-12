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
  name = "paper_author_affiliations",
  indexes = {
    @Index(
      name = "idx_paper_author_affiliations_author_order",
      columnList = "paper_author_id,display_order,id"
    ),
    @Index(name = "idx_paper_author_affiliations_institution", columnList = "institution_id")
  }
)
public class PaperAuthorAffiliation {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  @Column(name = "id")
  private Long id;

  @ManyToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "paper_author_id", nullable = false)
  private PaperAuthor paperAuthor;

  @ManyToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "institution_id", nullable = false)
  private Institution institution;

  @Column(name = "organization_name", nullable = false)
  private String organizationName;

  @Column
  private String department;

  @Column(name = "address_line_1")
  private String addressLine1;

  @Column(name = "address_line_2")
  private String addressLine2;

  @Column(nullable = false)
  private String country;

  @Column
  private String region;

  @Column(nullable = false)
  private String city;

  @Column(name = "postal_code")
  private String postalCode;

  @Column(name = "primary_affiliation", nullable = false)
  private boolean primaryAffiliation;

  @Column(name = "display_order", nullable = false)
  private int displayOrder;
}
