package com.openisle.service;

import com.openisle.model.AiScreeningResult;
import com.openisle.model.PaperProfile;
import com.openisle.model.PaperScreeningStatus;
import org.springframework.stereotype.Service;

@Service
public class MockAiScreeningService {

  public AiScreeningResult screen(PaperProfile paper) {
    AiScreeningResult result = new AiScreeningResult();
    result.setPaper(paper);
    result.setStatus(PaperScreeningStatus.PASSED);
    result.setRiskLevel("LOW");
    result.setDetectedSubjectArea(paper.getSubjectArea());
    result.setDetectedPaperType(paper.getPaperType());
    result.setSummary("The submission passed the MVP screening checks.");
    result.setIssuesJson("[]");
    result.setRawResponseJson("{\"provider\":\"mock\",\"status\":\"PASSED\"}");
    return result;
  }
}
