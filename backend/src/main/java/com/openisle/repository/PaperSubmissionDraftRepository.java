package com.openisle.repository;

import com.openisle.model.PaperSubmissionDraft;
import com.openisle.model.PaperSubmissionDraftStatus;
import java.util.Optional;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface PaperSubmissionDraftRepository
  extends JpaRepository<PaperSubmissionDraft, Long> {
  Optional<PaperSubmissionDraft> findFirstByCreatedByIdAndStatusOrderByUpdatedAtDescIdDesc(
    Long createdById,
    PaperSubmissionDraftStatus status
  );

  Optional<PaperSubmissionDraft> findByIdAndCreatedById(Long id, Long createdById);

  @Lock(LockModeType.PESSIMISTIC_WRITE)
  @Query(
    "SELECT draft FROM PaperSubmissionDraft draft " +
    "JOIN FETCH draft.createdBy WHERE draft.id = :draftId"
  )
  Optional<PaperSubmissionDraft> findByIdForUpdate(@Param("draftId") Long draftId);
}
