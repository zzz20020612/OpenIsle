package com.openisle.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openisle.dto.PaperSubmissionDraftDto;
import com.openisle.dto.PaperSubmissionDraftPatchRequest;
import com.openisle.dto.PaperSubmissionFileDto;
import com.openisle.dto.PaperSubmissionResultDto;
import com.openisle.dto.PaperSubmissionSubmitRequest;
import com.openisle.dto.PaperSubmissionValidationDto;
import com.openisle.dto.PaperDetailDto;
import com.openisle.dto.PaperSubmitRequest;
import com.openisle.exception.DraftVersionConflictException;
import com.openisle.exception.NotFoundException;
import com.openisle.model.PaperSubmissionDraft;
import com.openisle.model.PaperSubmissionDraftKind;
import com.openisle.model.PaperSubmissionDraftStatus;
import com.openisle.model.PaperArticleStatus;
import com.openisle.model.PaperSubmissionFile;
import com.openisle.model.PaperProfile;
import com.openisle.model.User;
import com.openisle.repository.PaperProfileRepository;
import com.openisle.repository.PaperSubmissionDraftRepository;
import com.openisle.repository.PaperSubmissionFileRepository;
import com.openisle.repository.UserRepository;
import java.util.List;
import java.util.Optional;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class PaperSubmissionDraftService {

  private static final String DEFAULT_MANUSCRIPT_TYPE = "Research Article";
  private static final String DEFAULT_SECTION = "manuscript-type";

  private final PaperSubmissionDraftRepository draftRepository;
  private final PaperSubmissionFileRepository fileRepository;
  private final PaperProfileRepository paperProfileRepository;
  private final UserRepository userRepository;
  private final PaperSubmissionValidator validator;
  private final PaperArticleService articleService;
  private final PaperService paperService;
  private final ObjectMapper objectMapper;

  @Transactional
  public PaperSubmissionDraftDto createDraft(String username) {
    User user = requireUser(username);
    PaperSubmitRequest form = new PaperSubmitRequest();
    form.setPaperType(DEFAULT_MANUSCRIPT_TYPE);

    PaperSubmissionDraft draft = new PaperSubmissionDraft();
    draft.setCreatedBy(user);
    draft.setManuscriptType(DEFAULT_MANUSCRIPT_TYPE);
    draft.setFormDataJson(writeForm(form));
    draft.setCurrentSection(DEFAULT_SECTION);
    draft.setStatus(PaperSubmissionDraftStatus.IN_PROGRESS);
    return toDto(draftRepository.saveAndFlush(draft));
  }

  @Transactional(readOnly = true)
  public Optional<PaperSubmissionDraftDto> getCurrentDraft(
    String username,
    PaperSubmissionDraftKind kind
  ) {
    User user = requireUser(username);
    Optional<PaperSubmissionDraft> draft = switch (
      kind != null ? kind : PaperSubmissionDraftKind.ANY
    ) {
      case ORIGINAL -> draftRepository
        .findFirstByCreatedByIdAndStatusAndRevisionSourcePaperIsNullOrderByUpdatedAtDescIdDesc(
          user.getId(),
          PaperSubmissionDraftStatus.IN_PROGRESS
        );
      case REVISION -> draftRepository
        .findFirstByCreatedByIdAndStatusAndRevisionSourcePaperIsNotNullOrderByUpdatedAtDescIdDesc(
          user.getId(),
          PaperSubmissionDraftStatus.IN_PROGRESS
        );
      case ANY -> draftRepository.findFirstByCreatedByIdAndStatusOrderByUpdatedAtDescIdDesc(
        user.getId(),
        PaperSubmissionDraftStatus.IN_PROGRESS
      );
    };
    return draft.map(this::toDto);
  }

  @Transactional(readOnly = true)
  public PaperSubmissionDraftDto getDraft(String username, Long draftId) {
    return toDto(requireOwnedDraft(username, draftId));
  }

  @Transactional
  public PaperSubmissionDraftDto updateDraft(
    String username,
    Long draftId,
    PaperSubmissionDraftPatchRequest request
  ) {
    PaperSubmissionDraft draft = requireOwnedDraft(username, draftId);
    requireEditable(draft);
    if (request == null || request.getVersion() != draft.getVersion()) {
      throw new DraftVersionConflictException(draft.getVersion());
    }
    PaperSubmitRequest form = request.getFormData() != null
      ? request.getFormData()
      : readForm(draft.getFormDataJson());
    draft.setFormDataJson(writeForm(form));
    draft.setManuscriptType(clean(form.getPaperType()));
    if (clean(request.getCurrentSection()) != null) {
      draft.setCurrentSection(clean(request.getCurrentSection()));
    }
    return toDto(draftRepository.saveAndFlush(draft));
  }

  @Transactional
  public void discardDraft(String username, Long draftId) {
    PaperSubmissionDraft draft = requireOwnedDraft(username, draftId);
    requireEditable(draft);
    draft.setStatus(PaperSubmissionDraftStatus.ABANDONED);
    draftRepository.save(draft);
  }

  @Transactional(readOnly = true)
  public PaperSubmissionValidationDto validateDraft(String username, Long draftId) {
    PaperSubmissionDraft draft = requireOwnedDraft(username, draftId);
    return validator.validateDraft(
      readForm(draft.getFormDataJson()),
      fileRepository.findByDraftIdOrderBySortOrderAscIdAsc(draft.getId())
    );
  }

  @Transactional
  public PaperSubmissionResultDto submitDraft(
    String username,
    Long draftId,
    PaperSubmissionSubmitRequest request
  ) {
    User user = requireUser(username);
    PaperSubmissionDraft draft = draftRepository
      .findByIdForUpdate(draftId)
      .orElseThrow(() -> new NotFoundException("Submission draft not found"));
    if (!draft.getCreatedBy().getId().equals(user.getId())) {
      throw new AccessDeniedException("You do not have access to this submission draft");
    }
    if (draft.getStatus() == PaperSubmissionDraftStatus.SUBMITTED) {
      if (draft.getSubmittedPaper() == null) {
        throw new IllegalStateException("Submitted draft has no linked paper");
      }
      return toSubmissionResult(draft.getSubmittedPaper());
    }
    requireEditable(draft);
    if (draft.getArticleStatus() != PaperArticleStatus.READY) {
      throw new IllegalArgumentException("Complete and approve the online article before submitting");
    }
    if (request == null || request.getVersion() != draft.getVersion()) {
      throw new DraftVersionConflictException(draft.getVersion());
    }

    PaperSubmitRequest form = readForm(draft.getFormDataJson());
    List<PaperSubmissionFile> files = fileRepository.findByDraftIdOrderBySortOrderAscIdAsc(
      draft.getId()
    );
    PaperSubmissionValidationDto validation = validator.validateForSubmission(
      form,
      files,
      request
    );
    if (!validation.isValid()) {
      String message = validation
        .getIssues()
        .stream()
        .findFirst()
        .map(issue -> issue.getMessage())
        .orElse("Submission validation failed");
      throw new IllegalArgumentException(message);
    }

    PaperDetailDto submitted = paperService.submitPaper(username, form, files);
    PaperProfile paper = paperProfileRepository
      .findById(submitted.getId())
      .orElseThrow(() -> new IllegalStateException("Submitted paper could not be loaded"));
    articleService.copyToPaper(draft, paper);
    paperProfileRepository.saveAndFlush(paper);
    draft.setSubmittedPaper(paper);
    draft.setIdempotencyKey(clean(request.getIdempotencyKey()));
    draft.setStatus(PaperSubmissionDraftStatus.SUBMITTED);
    draftRepository.saveAndFlush(draft);
    return toSubmissionResult(paper);
  }

  @Transactional(readOnly = true)
  public PaperSubmissionDraft requireOwnedDraft(String username, Long draftId) {
    User user = requireUser(username);
    PaperSubmissionDraft draft = draftRepository
      .findById(draftId)
      .orElseThrow(() -> new NotFoundException("Submission draft not found"));
    if (!draft.getCreatedBy().getId().equals(user.getId())) {
      throw new AccessDeniedException("You do not have access to this submission draft");
    }
    return draft;
  }

  private User requireUser(String username) {
    return userRepository
      .findByUsername(username)
      .orElseThrow(() -> new NotFoundException("User not found"));
  }

  private void requireEditable(PaperSubmissionDraft draft) {
    if (draft.getStatus() != PaperSubmissionDraftStatus.IN_PROGRESS) {
      throw new IllegalStateException("This submission draft is no longer editable");
    }
  }

  private PaperSubmissionDraftDto toDto(PaperSubmissionDraft draft) {
    PaperSubmissionDraftDto dto = new PaperSubmissionDraftDto();
    dto.setId(draft.getId());
    dto.setVersion(draft.getVersion());
    dto.setManuscriptType(draft.getManuscriptType());
    dto.setCurrentSection(draft.getCurrentSection());
    dto.setStatus(draft.getStatus());
    dto.setFormData(readForm(draft.getFormDataJson()));
    dto.setFiles(
      fileRepository
        .findByDraftIdOrderBySortOrderAscIdAsc(draft.getId())
        .stream()
        .map(this::toFileDto)
        .toList()
    );
    dto.setSubmittedPaperId(
      draft.getSubmittedPaper() != null ? draft.getSubmittedPaper().getId() : null
    );
    dto.setRevisionSourcePaperId(
      draft.getRevisionSourcePaper() != null ? draft.getRevisionSourcePaper().getId() : null
    );
    dto.setRevisionSourcePaperTitle(
      draft.getRevisionSourcePaper() != null ? draft.getRevisionSourcePaper().getTitle() : null
    );
    dto.setCreatedAt(draft.getCreatedAt());
    dto.setUpdatedAt(draft.getUpdatedAt());
    dto.setArticleStatus(draft.getArticleStatus());
    dto.setArticleVersion(draft.getArticleVersion());
    dto.setArticleReadyAt(draft.getArticleReadyAt());
    return dto;
  }

  private PaperSubmissionFileDto toFileDto(PaperSubmissionFile file) {
    PaperSubmissionFileDto dto = new PaperSubmissionFileDto();
    dto.setId(file.getId());
    dto.setOriginalFileName(file.getOriginalFileName());
    dto.setDisplayName(file.getDisplayName());
    dto.setContentType(file.getContentType());
    dto.setFileSize(file.getFileSize());
    dto.setRole(file.getRole());
    dto.setDescription(file.getDescription());
    dto.setVisibility(file.getVisibility());
    dto.setUploadStatus(file.getUploadStatus());
    dto.setSortOrder(file.getSortOrder());
    dto.setCreatedAt(file.getCreatedAt());
    dto.setUpdatedAt(file.getUpdatedAt());
    return dto;
  }

  private PaperSubmissionResultDto toSubmissionResult(PaperProfile paper) {
    PaperSubmissionResultDto result = new PaperSubmissionResultDto();
    result.setPaperId(paper.getId());
    result.setPostId(paper.getPost().getId());
    result.setPublicationStatus(paper.getPublicationStatus());
    result.setScreeningStatus(paper.getScreeningStatus());
    return result;
  }

  private String writeForm(PaperSubmitRequest form) {
    try {
      return objectMapper.writeValueAsString(form);
    } catch (JsonProcessingException exception) {
      throw new IllegalArgumentException("Unable to save submission draft", exception);
    }
  }

  private PaperSubmitRequest readForm(String value) {
    if (value == null || value.isBlank()) {
      return new PaperSubmitRequest();
    }
    try {
      return objectMapper.readValue(value, PaperSubmitRequest.class);
    } catch (JsonProcessingException exception) {
      throw new IllegalStateException("Unable to read submission draft", exception);
    }
  }

  private static String clean(String value) {
    return value == null || value.isBlank() ? null : value.trim();
  }
}
