package com.openisle.repository;

import com.openisle.model.PaperAuthorAffiliation;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PaperAuthorAffiliationRepository
  extends JpaRepository<PaperAuthorAffiliation, Long> {
  List<PaperAuthorAffiliation> findByPaperAuthorIdOrderByDisplayOrderAscIdAsc(
    Long paperAuthorId
  );
}
