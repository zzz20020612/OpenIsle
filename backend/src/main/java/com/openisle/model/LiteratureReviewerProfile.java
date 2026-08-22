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
@Table(name = "literature_reviewer_profiles")
public class LiteratureReviewerProfile {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @OneToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "user_id", nullable = false, unique = true)
  private User user;

  @Column(nullable = false)
  private int points;
  @Column(nullable = false)
  private int acceptedTasks;
  @Column(nullable = false)
  private int completedTasks;
  @Column(nullable = false)
  private int onTimeTasks;
  @Column(nullable = false)
  private double creditScore = 75.0;
  @Column(nullable = false, length = 1)
  private String level = "B";
  @Column(nullable = false)
  private boolean eligible = true;

  @CreationTimestamp @Column(nullable = false, updatable = false)
  private LocalDateTime createdAt;
  @UpdateTimestamp @Column(nullable = false)
  private LocalDateTime updatedAt;
}
