package com.openisle.repository;

import com.openisle.model.LiteratureScoreSnapshot;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface LiteratureScoreSnapshotRepository extends JpaRepository<LiteratureScoreSnapshot, Long> {
  Optional<LiteratureScoreSnapshot> findByLiteraturePaperId(Long literaturePaperId);
}
