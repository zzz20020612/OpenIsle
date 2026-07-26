package com.openisle.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
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
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class AiScreeningProcessorTest {

  @Test
  void publishesPaperWhenScreeningServicePassesIt() {
    PaperProfile paper = paper(10L);
    PaperFile file = manuscript(paper);
    var paperRepository = mock(PaperProfileRepository.class);
    var fileRepository = mock(PaperFileRepository.class);
    var authorRepository = mock(PaperAuthorRepository.class);
    var resultRepository = mock(AiScreeningResultRepository.class);
    var storage = mock(PresignedFileStorageService.class);
    var client = mock(AiScreeningClient.class);
    when(paperRepository.findById(10L)).thenReturn(Optional.of(paper));
    when(fileRepository.findByPaperIdOrderBySortOrderAscIdAsc(10L)).thenReturn(List.of(file));
    when(authorRepository.findByPaperIdOrderByAuthorOrderAsc(10L)).thenReturn(List.of());
    when(storage.presignDownload("papers/manuscript.pdf", "manuscript.pdf", false))
      .thenReturn("http://springboot/download/token");
    when(client.screen(any())).thenReturn(response("PASSED", "publish", "LOW"));

    new AiScreeningProcessor(
      paperRepository,
      fileRepository,
      authorRepository,
      resultRepository,
      storage,
      client,
      new ObjectMapper()
    ).process(10L);

    assertEquals(PaperScreeningStatus.PASSED, paper.getScreeningStatus());
    assertEquals(PaperPublicationStatus.PUBLISHED, paper.getPublicationStatus());
    ArgumentCaptor<AiScreeningResult> captor = ArgumentCaptor.forClass(AiScreeningResult.class);
    verify(resultRepository).save(captor.capture());
    assertEquals("LOW", captor.getValue().getRiskLevel());
  }

  @Test
  void recordsFailedWithoutRejectingPaperWhenServiceThrows() {
    PaperProfile paper = paper(11L);
    PaperFile file = manuscript(paper);
    var paperRepository = mock(PaperProfileRepository.class);
    var fileRepository = mock(PaperFileRepository.class);
    var authorRepository = mock(PaperAuthorRepository.class);
    var resultRepository = mock(AiScreeningResultRepository.class);
    var storage = mock(PresignedFileStorageService.class);
    var client = mock(AiScreeningClient.class);
    when(paperRepository.findById(11L)).thenReturn(Optional.of(paper));
    when(fileRepository.findByPaperIdOrderBySortOrderAscIdAsc(11L)).thenReturn(List.of(file));
    when(authorRepository.findByPaperIdOrderByAuthorOrderAsc(11L)).thenReturn(List.of());
    when(storage.presignDownload(any(), any(), any(Boolean.class))).thenReturn("http://file");
    when(client.screen(any())).thenThrow(new IllegalStateException("model unavailable"));

    new AiScreeningProcessor(
      paperRepository,
      fileRepository,
      authorRepository,
      resultRepository,
      storage,
      client,
      new ObjectMapper()
    ).process(11L);

    assertEquals(PaperScreeningStatus.FAILED, paper.getScreeningStatus());
    assertEquals(PaperPublicationStatus.SCREENING, paper.getPublicationStatus());
    ArgumentCaptor<AiScreeningResult> captor = ArgumentCaptor.forClass(AiScreeningResult.class);
    verify(resultRepository).save(captor.capture());
    assertEquals("UNKNOWN", captor.getValue().getRiskLevel());
  }

  private static PaperProfile paper(Long id) {
    PaperProfile paper = new PaperProfile();
    paper.setId(id);
    paper.setTitle("Paper");
    paper.setSubjectArea("Biology");
    paper.setPaperType("Research Article");
    paper.setPublicationStatus(PaperPublicationStatus.SCREENING);
    paper.setScreeningStatus(PaperScreeningStatus.SCREENING);
    return paper;
  }

  private static PaperFile manuscript(PaperProfile paper) {
    PaperFile file = new PaperFile();
    file.setPaper(paper);
    file.setRole(PaperFileRole.MANUSCRIPT);
    file.setStorageKey("papers/manuscript.pdf");
    file.setDisplayName("manuscript.pdf");
    file.setOriginalFileName("manuscript.pdf");
    return file;
  }

  private static AiScreeningServiceResponse response(String status, String verdict, String risk) {
    AiScreeningServiceResponse response = new AiScreeningServiceResponse();
    response.setPaperId(10L);
    response.setStatus(status);
    response.setVerdict(verdict);
    response.setRiskLevel(risk);
    response.setSummary("screened");
    response.setDimensions(List.of());
    response.setSkippedDimensions(List.of("02", "03"));
    response.setReportMarkdown("report");
    response.setRawResult(java.util.Map.of());
    return response;
  }
}
