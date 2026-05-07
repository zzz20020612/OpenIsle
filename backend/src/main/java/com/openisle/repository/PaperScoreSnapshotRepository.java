package com.openisle.repository;

import com.openisle.model.PaperScoreSnapshot;
import com.openisle.model.PaperPublicationStatus;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PaperScoreSnapshotRepository extends JpaRepository<PaperScoreSnapshot, Long> {
  Optional<PaperScoreSnapshot> findByPaperId(Long paperId);

  List<PaperScoreSnapshot> findByRatingCountGreaterThanOrderByCompositeScoreDesc(
    int ratingCount,
    Pageable pageable
  );

  List<PaperScoreSnapshot> findByRatingCountGreaterThan(int ratingCount);

  List<PaperScoreSnapshot> findByRatingCountGreaterThanAndPaperPublicationStatusOrderByCompositeScoreDesc(
    int ratingCount,
    PaperPublicationStatus publicationStatus,
    Pageable pageable
  );

  List<PaperScoreSnapshot> findByRatingCountGreaterThanAndPaperPublicationStatus(
    int ratingCount,
    PaperPublicationStatus publicationStatus
  );
}
