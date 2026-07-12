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
  name = "paper_funding_records",
  indexes = {
    @Index(name = "idx_paper_funding_records_paper_order", columnList = "paper_id,display_order,id")
  }
)
public class PaperFundingRecord {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  @Column(name = "id")
  private Long id;

  @ManyToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "paper_id", nullable = false)
  private PaperProfile paper;

  @Column(name = "funder_name", nullable = false)
  private String funderName;

  @Column(name = "grant_id")
  private String grantId;

  @Column(name = "display_order", nullable = false)
  private int displayOrder;
}
