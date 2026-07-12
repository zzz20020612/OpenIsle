package com.openisle.repository;

import com.openisle.model.PaperFile;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface PaperFileRepository extends JpaRepository<PaperFile, Long> {
  List<PaperFile> findByPaperIdOrderBySortOrderAscIdAsc(Long paperId);

  Optional<PaperFile> findByIdAndPaperId(Long id, Long paperId);

  @Modifying(clearAutomatically = true, flushAutomatically = true)
  @Query("UPDATE PaperFile file SET file.viewCount = file.viewCount + 1 WHERE file.id = :fileId")
  int incrementViewCount(@Param("fileId") Long fileId);

  @Modifying(clearAutomatically = true, flushAutomatically = true)
  @Query(
    "UPDATE PaperFile file SET file.downloadCount = file.downloadCount + 1 WHERE file.id = :fileId"
  )
  int incrementDownloadCount(@Param("fileId") Long fileId);
}
