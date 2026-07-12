package com.openisle.repository;

import com.openisle.model.PaperProfile;
import com.openisle.model.PaperPublicationStatus;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface PaperProfileRepository extends JpaRepository<PaperProfile, Long> {
  Optional<PaperProfile> findByPostId(Long postId);

  List<PaperProfile> findByPublicationStatusOrderByPublishedAtDesc(
    PaperPublicationStatus status,
    Pageable pageable
  );

  List<PaperProfile> findByPublicationStatusOrderByCreatedAtDesc(
    PaperPublicationStatus status,
    Pageable pageable
  );

  List<PaperProfile> findByPublicationStatusAndSubjectAreaIgnoreCaseOrderByPublishedAtDesc(
    PaperPublicationStatus status,
    String subjectArea,
    Pageable pageable
  );

  @Query(
    """
    SELECT p
    FROM PaperProfile p
    LEFT JOIN PaperScoreSnapshot s ON s.paper = p
    WHERE p.publicationStatus = com.openisle.model.PaperPublicationStatus.PUBLISHED
      AND (:subjectArea IS NULL OR LOWER(p.subjectArea) = LOWER(:subjectArea))
      AND (:minScore IS NULL OR COALESCE(s.compositeScore, 0) >= :minScore)
    ORDER BY COALESCE(s.compositeScore, 0) DESC,
      COALESCE(s.ratingCount, 0) DESC,
      p.publishedAt DESC,
      p.id DESC
    """
  )
  List<PaperProfile> findPublishedOrderByScoreDesc(
    @Param("subjectArea") String subjectArea,
    @Param("minScore") Double minScore,
    Pageable pageable
  );

  List<PaperProfile> findDistinctByPublicationStatusOrderBySubjectAreaAsc(
    PaperPublicationStatus status
  );
}
