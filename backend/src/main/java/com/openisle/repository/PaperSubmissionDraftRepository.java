package com.openisle.repository;

import com.openisle.model.PaperSubmissionDraft;
import com.openisle.model.PaperSubmissionDraftStatus;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PaperSubmissionDraftRepository
  extends JpaRepository<PaperSubmissionDraft, Long> {
  Optional<PaperSubmissionDraft> findFirstByCreatedByIdAndStatusOrderByUpdatedAtDescIdDesc(
    Long createdById,
    PaperSubmissionDraftStatus status
  );

  Optional<PaperSubmissionDraft> findByIdAndCreatedById(Long id, Long createdById);
}
