package com.openisle.repository;

import com.openisle.model.LiteratureRating;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface LiteratureRatingRepository extends JpaRepository<LiteratureRating, Long> {
  Optional<LiteratureRating> findByLiteraturePaperIdAndRaterId(Long literaturePaperId, Long raterId);

  List<LiteratureRating> findByLiteraturePaperIdOrderByUpdatedAtDesc(Long literaturePaperId);

  List<LiteratureRating> findByLiteraturePaperId(Long literaturePaperId);

  boolean existsByLiteraturePaperIdAndRaterId(Long literaturePaperId, Long raterId);
}
