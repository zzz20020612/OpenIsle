package com.openisle.repository;

import com.openisle.model.PaperAuthor;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PaperAuthorRepository extends JpaRepository<PaperAuthor, Long> {
  List<PaperAuthor> findByPaperIdOrderByAuthorOrderAsc(Long paperId);

  List<PaperAuthor> findByExpertProfileIdOrderByPaperPublishedAtDescAuthorOrderAsc(Long expertProfileId);
}
