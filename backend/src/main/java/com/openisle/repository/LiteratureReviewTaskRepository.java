package com.openisle.repository;

import com.openisle.model.LiteratureReviewTask;
import com.openisle.model.LiteratureReviewTaskStatus;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface LiteratureReviewTaskRepository extends JpaRepository<LiteratureReviewTask, Long> {
  List<LiteratureReviewTask> findByReviewerIdOrderByClaimedAtDesc(Long reviewerId);
  Optional<LiteratureReviewTask> findByLiteraturePaperIdAndReviewerId(Long paperId, Long reviewerId);
  Optional<LiteratureReviewTask> findByLiteraturePaperIdAndReviewerIdAndStatus(Long paperId, Long reviewerId, LiteratureReviewTaskStatus status);
}
