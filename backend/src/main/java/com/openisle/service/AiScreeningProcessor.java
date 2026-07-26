package com.openisle.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openisle.dto.AiScreeningServiceRequest;
import com.openisle.dto.AiScreeningServiceResponse;
import com.openisle.model.AiScreeningResult;
import com.openisle.model.PaperFile;
import com.openisle.model.PaperFileRole;
import com.openisle.model.PaperProfile;
import com.openisle.model.PaperPublicationStatus;
import com.openisle.model.PaperScreeningStatus;
import com.openisle.repository.AiScreeningResultRepository;
import com.openisle.repository.PaperAuthorRepository;
import com.openisle.repository.PaperFileRepository;
import com.openisle.repository.PaperProfileRepository;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

@Service
@RequiredArgsConstructor
public class AiScreeningProcessor {

  private final PaperProfileRepository paperProfileRepository;
  private final PaperFileRepository paperFileRepository;
  private final PaperAuthorRepository paperAuthorRepository;
  private final AiScreeningResultRepository aiScreeningResultRepository;
  private final PresignedFileStorageService storageService;
  private final AiScreeningClient client;
  private final ObjectMapper objectMapper;

  @Async("notificationExecutor")
  @Transactional
  @TransactionalEventListener(
    phase = TransactionPhase.AFTER_COMMIT,
    fallbackExecution = true
  )
  public void onRequested(AiScreeningRequestedEvent event) {
    process(event.paperId());
  }

  @Transactional
  public void process(Long paperId) {
    PaperProfile paper = paperProfileRepository
      .findById(paperId)
      .orElseThrow(() -> new IllegalArgumentException("Paper not found: " + paperId));
    try {
      PaperFile manuscript = paperFileRepository
        .findByPaperIdOrderBySortOrderAscIdAsc(paperId)
        .stream()
        .filter(file -> file.getRole() == PaperFileRole.MANUSCRIPT)
        .findFirst()
        .orElseThrow(() -> new IllegalStateException("Manuscript file not found"));
      String manuscriptUrl = storageService.presignDownload(
        manuscript.getStorageKey(),
        manuscript.getDisplayName(),
        false
      );
      List<String> authors = paperAuthorRepository
        .findByPaperIdOrderByAuthorOrderAsc(paperId)
        .stream()
        .map(author -> author.getDisplayName())
        .toList();
      AiScreeningServiceResponse response = client.screen(
        new AiScreeningServiceRequest(
          paperId,
          manuscriptUrl,
          manuscript.getOriginalFileName(),
          paper.getTitle(),
          authors,
          paper.getSubjectArea(),
          paper.getPaperType(),
          declarations(paper)
        )
      );
      if (response == null) {
        throw new IllegalStateException("AI screening service returned an empty response");
      }
      saveSuccess(paper, response);
    } catch (Exception exception) {
      saveFailure(paper, exception);
    }
    paperProfileRepository.save(paper);
  }

  private void saveSuccess(PaperProfile paper, AiScreeningServiceResponse response) {
    PaperScreeningStatus status = PaperScreeningStatus.valueOf(response.getStatus());
    paper.setScreeningStatus(status);
    if (status == PaperScreeningStatus.PASSED) {
      paper.setPublicationStatus(PaperPublicationStatus.PUBLISHED);
      paper.setPublishedAt(LocalDateTime.now());
    } else if (status == PaperScreeningStatus.NEEDS_REVISION) {
      paper.setPublicationStatus(PaperPublicationStatus.NEEDS_REVISION);
    } else if (status == PaperScreeningStatus.REJECTED_BY_POLICY) {
      paper.setPublicationStatus(PaperPublicationStatus.REJECTED);
    }

    AiScreeningResult result = baseResult(paper);
    result.setStatus(status);
    result.setRiskLevel(response.getRiskLevel());
    result.setDetectedSubjectArea(paper.getSubjectArea());
    result.setDetectedPaperType(paper.getPaperType());
    result.setSummary(response.getSummary());
    result.setIssuesJson(writeJson(response.getDimensions()));
    result.setRawResponseJson(writeJson(response));
    aiScreeningResultRepository.save(result);
  }

  private void saveFailure(PaperProfile paper, Exception exception) {
    paper.setScreeningStatus(PaperScreeningStatus.FAILED);
    AiScreeningResult result = baseResult(paper);
    result.setStatus(PaperScreeningStatus.FAILED);
    result.setRiskLevel("UNKNOWN");
    result.setSummary("AI screening failed: " + exception.getMessage());
    result.setIssuesJson("[]");
    result.setRawResponseJson(writeJson(Map.of("error", exception.getClass().getSimpleName())));
    aiScreeningResultRepository.save(result);
  }

  private static AiScreeningResult baseResult(PaperProfile paper) {
    AiScreeningResult result = new AiScreeningResult();
    result.setPaper(paper);
    return result;
  }

  private static Map<String, String> declarations(PaperProfile paper) {
    Map<String, String> values = new LinkedHashMap<>();
    putIfPresent(values, "fundingStatement", paper.getFundingStatement());
    putIfPresent(values, "conflictOfInterest", paper.getConflictOfInterest());
    putIfPresent(values, "dataAvailability", paper.getDataAvailability());
    putIfPresent(values, "ethicsStatement", paper.getEthicsStatement());
    putIfPresent(values, "aiUseDisclosure", paper.getAiUseDisclosure());
    return values;
  }

  private static void putIfPresent(Map<String, String> values, String key, String value) {
    if (value != null && !value.isBlank()) {
      values.put(key, value);
    }
  }

  private String writeJson(Object value) {
    try {
      return objectMapper.writeValueAsString(value);
    } catch (JsonProcessingException exception) {
      throw new IllegalStateException("Could not serialize screening result", exception);
    }
  }
}
