package com.openisle.repository;

import com.openisle.model.PaperRating;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PaperRatingRepository extends JpaRepository<PaperRating, Long> {
  Optional<PaperRating> findByPaperIdAndRaterId(Long paperId, Long raterId);

  List<PaperRating> findByPaperId(Long paperId);
}
