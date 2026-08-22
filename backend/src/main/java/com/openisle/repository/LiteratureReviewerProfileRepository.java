package com.openisle.repository;

import com.openisle.model.LiteratureReviewerProfile;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface LiteratureReviewerProfileRepository extends JpaRepository<LiteratureReviewerProfile, Long> {
  Optional<LiteratureReviewerProfile> findByUserId(Long userId);
}
