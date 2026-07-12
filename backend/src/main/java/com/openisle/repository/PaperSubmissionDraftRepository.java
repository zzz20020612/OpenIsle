package com.openisle.repository;

import com.openisle.model.PaperSubmissionDraft;
import com.openisle.model.PaperSubmissionDraftStatus;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PaperSubmissionDraftRepository
  extends JpaRepository<PaperSubmissionDraft, Long> {
  Optional<PaperSubmissionDraft> findFirstByOwnerIdAndStatusOrderByUpdatedAtDescIdDesc(
    Long ownerId,
    PaperSubmissionDraftStatus status
  );
}
