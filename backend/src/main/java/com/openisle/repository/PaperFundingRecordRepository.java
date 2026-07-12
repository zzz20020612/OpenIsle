package com.openisle.repository;

import com.openisle.model.PaperFundingRecord;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PaperFundingRecordRepository extends JpaRepository<PaperFundingRecord, Long> {
  List<PaperFundingRecord> findByPaperIdOrderByDisplayOrderAscIdAsc(Long paperId);
}
