package com.openisle.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openisle.dto.PaperArticleDto;
import com.openisle.dto.PaperArticleValidationDto;
import com.openisle.exception.DraftVersionConflictException;
import com.openisle.exception.NotFoundException;
import com.openisle.model.PaperArticleStatus;
import com.openisle.model.PaperProfile;
import com.openisle.model.PaperSubmissionDraft;
import com.openisle.model.PaperSubmissionDraftStatus;
import com.openisle.model.PaperSubmissionFile;
import com.openisle.model.User;
import com.openisle.repository.PaperProfileRepository;
import com.openisle.repository.PaperSubmissionDraftRepository;
import com.openisle.repository.PaperSubmissionFileRepository;
import com.openisle.repository.UserRepository;
import java.time.LocalDateTime;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class PaperArticleService {

  private final PaperSubmissionDraftRepository draftRepository;
  private final PaperSubmissionFileRepository fileRepository;
  private final PaperProfileRepository paperProfileRepository;
  private final UserRepository userRepository;
  private final PaperArticleValidator validator;
  private final PaperAccessPolicy paperAccessPolicy;
  private final ObjectMapper objectMapper;

  @Transactional(readOnly = true)
  public PaperArticleDto getDraftArticle(String username, Long draftId) {
    return toDto(requireOwnedDraft(username, draftId));
  }

  @Transactional
  public PaperArticleDto updateDraftArticle(String username, Long draftId, PaperArticleDto request) {
    PaperSubmissionDraft draft = requireOwnedDraft(username, draftId);
    requireEditable(draft);
    requireVersion(draft, request);
    PaperArticleDto article = request == null ? new PaperArticleDto() : request;
    article.setVersion(draft.getArticleVersion() + 1);
    article.setStatus(PaperArticleStatus.IN_PROGRESS);
    article.setReadyAt(null);
    draft.setArticleJson(write(article));
    draft.setArticleVersion(article.getVersion());
    draft.setArticleStatus(article.getStatus());
    draft.setArticleReadyAt(null);
    draftRepository.saveAndFlush(draft);
    return toDto(draft);
  }

  @Transactional(readOnly = true)
  public PaperArticleValidationDto validateDraftArticle(String username, Long draftId) {
    PaperSubmissionDraft draft = requireOwnedDraft(username, draftId);
    return validator.validate(toDto(draft), files(draft));
  }

  @Transactional
  public PaperArticleDto markReady(String username, Long draftId, PaperArticleDto request) {
    PaperSubmissionDraft draft = requireOwnedDraft(username, draftId);
    requireEditable(draft);
    requireVersion(draft, request);
    PaperArticleDto article = request == null ? toDto(draft) : request;
    PaperArticleValidationDto validation = validator.validate(article, files(draft));
    if (!validation.isValid()) {
      throw new IllegalArgumentException("Article content is not ready for submission");
    }
    article.setStatus(PaperArticleStatus.READY);
    article.setVersion(draft.getArticleVersion() + 1);
    article.setReadyAt(LocalDateTime.now());
    draft.setArticleJson(write(article));
    draft.setArticleVersion(article.getVersion());
    draft.setArticleStatus(article.getStatus());
    draft.setArticleReadyAt(article.getReadyAt());
    draftRepository.saveAndFlush(draft);
    return toDto(draft);
  }

  @Transactional
  public PaperArticleDto reopen(String username, Long draftId) {
    PaperSubmissionDraft draft = requireOwnedDraft(username, draftId);
    requireEditable(draft);
    PaperArticleDto article = toDto(draft);
    article.setStatus(PaperArticleStatus.IN_PROGRESS);
    article.setReadyAt(null);
    article.setVersion(draft.getArticleVersion() + 1);
    draft.setArticleJson(write(article));
    draft.setArticleVersion(article.getVersion());
    draft.setArticleStatus(article.getStatus());
    draft.setArticleReadyAt(null);
    draftRepository.saveAndFlush(draft);
    return toDto(draft);
  }

  @Transactional(readOnly = true)
  public PaperArticleDto getPublishedArticle(Long paperId) {
    PaperProfile paper = paperProfileRepository.findById(paperId)
      .orElseThrow(() -> new NotFoundException("Paper not found"));
    if (!paperAccessPolicy.canAppearInFeed(paper)) {
      throw new NotFoundException("Paper not found");
    }
    return read(paper.getArticleJson());
  }

  public void copyToPaper(PaperSubmissionDraft draft, PaperProfile paper) {
    if (draft.getArticleStatus() != PaperArticleStatus.READY) {
      throw new IllegalArgumentException("Article content must be ready before submission");
    }
    PaperArticleDto article = toDto(draft);
    PaperArticleValidationDto validation = validator.validate(article, files(draft));
    if (!validation.isValid()) {
      throw new IllegalArgumentException("Article content is not ready for submission");
    }
    paper.setArticleJson(write(article));
  }

  private PaperSubmissionDraft requireOwnedDraft(String username, Long draftId) {
    User user = userRepository.findByUsername(username)
      .orElseThrow(() -> new NotFoundException("User not found"));
    PaperSubmissionDraft draft = draftRepository.findById(draftId)
      .orElseThrow(() -> new NotFoundException("Submission draft not found"));
    if (!draft.getCreatedBy().getId().equals(user.getId())) {
      throw new AccessDeniedException("You do not have access to this submission draft");
    }
    return draft;
  }

  private void requireEditable(PaperSubmissionDraft draft) {
    if (draft.getStatus() != PaperSubmissionDraftStatus.IN_PROGRESS) {
      throw new IllegalStateException("This submission draft is no longer editable");
    }
  }

  private void requireVersion(PaperSubmissionDraft draft, PaperArticleDto request) {
    if (request == null || request.getVersion() != draft.getArticleVersion()) {
      throw new DraftVersionConflictException(draft.getArticleVersion());
    }
  }

  private List<PaperSubmissionFile> files(PaperSubmissionDraft draft) {
    return fileRepository.findByDraftIdOrderBySortOrderAscIdAsc(draft.getId());
  }

  private PaperArticleDto toDto(PaperSubmissionDraft draft) {
    PaperArticleDto article = read(draft.getArticleJson());
    article.setVersion(draft.getArticleVersion());
    article.setStatus(draft.getArticleStatus());
    article.setReadyAt(draft.getArticleReadyAt());
    article.setUpdatedAt(draft.getUpdatedAt());
    return article;
  }

  private PaperArticleDto read(String value) {
    if (value == null || value.isBlank()) return new PaperArticleDto();
    try {
      return objectMapper.readValue(value, PaperArticleDto.class);
    } catch (JsonProcessingException exception) {
      throw new IllegalStateException("Unable to read structured article", exception);
    }
  }

  private String write(PaperArticleDto article) {
    try {
      return objectMapper.writeValueAsString(article);
    } catch (JsonProcessingException exception) {
      throw new IllegalArgumentException("Unable to save structured article", exception);
    }
  }
}
