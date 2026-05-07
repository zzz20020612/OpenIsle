package com.openisle.repository;

import com.openisle.model.Institution;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface InstitutionRepository extends JpaRepository<Institution, Long> {
  Optional<Institution> findByNameIgnoreCase(String name);
}
