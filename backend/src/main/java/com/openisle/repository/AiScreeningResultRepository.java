package com.openisle.repository;

import com.openisle.model.AiScreeningResult;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AiScreeningResultRepository extends JpaRepository<AiScreeningResult, Long> {
  Optional<AiScreeningResult> findFirstByPaperIdOrderByScreenedAtDesc(Long paperId);
}
