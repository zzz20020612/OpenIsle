package com.openisle.repository;

import com.openisle.model.PaperSubmissionFile;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PaperSubmissionFileRepository
  extends JpaRepository<PaperSubmissionFile, Long> {
  List<PaperSubmissionFile> findByDraftIdOrderBySortOrderAscIdAsc(Long draftId);

  Optional<PaperSubmissionFile> findByIdAndDraftId(Long id, Long draftId);
}
