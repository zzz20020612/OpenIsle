package com.openisle.repository;

import com.openisle.model.PaperFile;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PaperFileRepository extends JpaRepository<PaperFile, Long> {
  List<PaperFile> findByPaperIdOrderBySortOrderAscIdAsc(Long paperId);
}
