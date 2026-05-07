package com.openisle.repository;

import com.openisle.model.PaperProfile;
import com.openisle.model.PaperPublicationStatus;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

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

  List<PaperProfile> findDistinctByPublicationStatusOrderBySubjectAreaAsc(
    PaperPublicationStatus status
  );
}
