package com.openisle.repository;

import com.openisle.model.ExpertProfile;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ExpertProfileRepository extends JpaRepository<ExpertProfile, Long> {
  Optional<ExpertProfile> findByOrcid(String orcid);

  Optional<ExpertProfile> findByEmailIgnoreCase(String email);
}
