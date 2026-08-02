package com.openisle.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openisle.dto.PaperSubmissionDraftDto;
import com.openisle.dto.PaperSubmissionDraftPatchRequest;
import com.openisle.dto.PaperSubmissionDraftRenameRequest;
import com.openisle.dto.PaperSubmissionFileDto;
import com.openisle.dto.PaperSubmissionResultDto;
import com.openisle.dto.PaperSubmissionSubmitRequest;
import com.openisle.dto.PaperSubmissionValidationDto;
import com.openisle.dto.PaperDetailDto;
import com.openisle.dto.PaperAffiliationRequest;
import com.openisle.dto.PaperArticleDto;
import com.openisle.dto.PaperAuthorRequest;
import com.openisle.dto.PaperFundingRequest;
import com.openisle.dto.PaperSubmitRequest;
import com.openisle.exception.DraftVersionConflictException;
import com.openisle.exception.NotFoundException;
import com.openisle.model.PaperSubmissionDraft;
import com.openisle.model.PaperSubmissionDraftKind;
import com.openisle.model.PaperSubmissionDraftStatus;
import com.openisle.model.PaperArticleStatus;
import com.openisle.model.PaperAuthor;
import com.openisle.model.PaperAuthorAffiliation;
import com.openisle.model.PaperFile;
import com.openisle.model.PaperFileRole;
import com.openisle.model.PaperPublicationStatus;
import com.openisle.model.PaperSubmissionFile;
import com.openisle.model.PaperProfile;
import com.openisle.model.User;
import com.openisle.repository.PaperProfileRepository;
import com.openisle.repository.PaperAuthorAffiliationRepository;
import com.openisle.repository.PaperAuthorRepository;
import com.openisle.repository.PaperFileRepository;
import com.openisle.repository.PaperFundingRecordRepository;
import com.openisle.repository.PaperSubmissionDraftRepository;
import com.openisle.repository.PaperSubmissionFileRepository;
import com.openisle.repository.UserRepository;
import java.util.HashMap;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
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
  private static final long STALE_DRAFT_DAYS = 30;

  private final PaperSubmissionDraftRepository draftRepository;
  private final PaperSubmissionFileRepository fileRepository;
  private final PaperProfileRepository paperProfileRepository;
  private final PaperAuthorRepository paperAuthorRepository;
  private final PaperAuthorAffiliationRepository paperAuthorAffiliationRepository;
  private final PaperFundingRecordRepository paperFundingRecordRepository;
  private final PaperFileRepository paperFileRepository;
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

  @Transactional
  public PaperSubmissionDraftDto createRevisionDraft(String username, Long paperId) {
    User user = requireUser(username);
    PaperProfile source = paperProfileRepository.findById(paperId)
      .orElseThrow(() -> new NotFoundException("Paper not found"));
    if (!source.getCreatedBy().getId().equals(user.getId())) {
      throw new AccessDeniedException("Only the submitting author can create a revision");
    }
    if (source.getPublicationStatus() != PaperPublicationStatus.NEEDS_REVISION) {
      throw new IllegalStateException("A revision can only be created for a paper that needs revision");
    }
    if (paperProfileRepository.findFirstByRevisionOfPaperIdOrderByRevisionNumberDescIdDesc(paperId).isPresent()) {
      throw new IllegalStateException("A newer revision has already been submitted for this paper");
    }
    var existing = draftRepository.findFirstByRevisionSourcePaperIdAndStatusOrderByUpdatedAtDescIdDesc(
      paperId,
      PaperSubmissionDraftStatus.IN_PROGRESS
    );
    if (existing.isPresent()) {
      return toDto(existing.get());
    }

    PaperSubmissionDraft draft = new PaperSubmissionDraft();
    draft.setCreatedBy(user);
    draft.setRevisionSourcePaper(source);
    draft.setManuscriptType(source.getPaperType());
    draft.setFormDataJson(writeForm(formFromPaper(source)));
    draft.setCurrentSection(DEFAULT_SECTION);
    draft.setStatus(PaperSubmissionDraftStatus.IN_PROGRESS);
    draft = draftRepository.saveAndFlush(draft);

    Map<Long, Long> revisionFileIds = copyFilesToRevisionDraft(source, draft);
    copyArticleToRevisionDraft(source, draft, revisionFileIds);
    draftRepository.saveAndFlush(draft);
    return toDto(draft);
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
  public List<PaperSubmissionDraftDto> listDrafts(
    String username,
    PaperSubmissionDraftKind kind
  ) {
    User user = requireUser(username);
    List<PaperSubmissionDraft> drafts = switch (
      kind != null ? kind : PaperSubmissionDraftKind.ANY
    ) {
      case ORIGINAL -> draftRepository
        .findByCreatedByIdAndStatusAndRevisionSourcePaperIsNullOrderByUpdatedAtDescIdDesc(
          user.getId(),
          PaperSubmissionDraftStatus.IN_PROGRESS
        );
      case REVISION -> draftRepository
        .findByCreatedByIdAndStatusAndRevisionSourcePaperIsNotNullOrderByUpdatedAtDescIdDesc(
          user.getId(),
          PaperSubmissionDraftStatus.IN_PROGRESS
        );
      case ANY -> draftRepository.findByCreatedByIdAndStatusOrderByUpdatedAtDescIdDesc(
        user.getId(),
        PaperSubmissionDraftStatus.IN_PROGRESS
      );
    };
    return drafts
      .stream()
      .filter(this::isMeaningfulDraft)
      .map(this::toDto)
      .toList();
  }

  @Transactional(readOnly = true)
  public PaperSubmissionDraftDto getDraft(String username, Long draftId) {
    return toDto(requireOwnedDraft(username, draftId));
  }

  private boolean isMeaningfulDraft(PaperSubmissionDraft draft) {
    if (draft.getRevisionSourcePaper() != null) {
      return true;
    }
    if (draft.getArticleStatus() == PaperArticleStatus.READY || hasMeaningfulArticle(draft.getArticleJson())) {
      return true;
    }
    if (!fileRepository.findByDraftIdOrderBySortOrderAscIdAsc(draft.getId()).isEmpty()) {
      return true;
    }
    return hasMeaningfulFormData(readForm(draft.getFormDataJson()));
  }

  private boolean hasMeaningfulFormData(PaperSubmitRequest form) {
    if (
      form.getCategoryId() != null ||
      hasValues(form.getTagIds()) ||
      hasText(form.getTitle()) ||
      hasText(form.getAbstractText()) ||
      hasValues(form.getKeywords()) ||
      hasValues(form.getReferences()) ||
      hasValues(form.getManuscriptFiles()) ||
      hasValues(form.getSupplementaryFiles()) ||
      hasText(form.getSubjectArea()) ||
      hasText(form.getContent()) ||
      hasText(form.getPrimaryInstitutionName()) ||
      hasText(form.getFundingStatement()) ||
      hasText(form.getConflictOfInterest()) ||
      hasText(form.getDataAvailability()) ||
      hasText(form.getEthicsStatement()) ||
      hasText(form.getPreprintStatement()) ||
      hasText(form.getAiUseDisclosure()) ||
      hasText(form.getPrivateComments()) ||
      Boolean.TRUE.equals(form.getNoFundingReceived()) ||
      Boolean.TRUE.equals(form.getAllAuthorsConsent()) ||
      Boolean.TRUE.equals(form.getOriginalityConfirmed()) ||
      Boolean.TRUE.equals(form.getRightsConfirmed()) ||
      Boolean.TRUE.equals(form.getCorrespondingAuthorContactConfirmed()) ||
      (hasText(form.getPaperType()) && !DEFAULT_MANUSCRIPT_TYPE.equals(form.getPaperType()))
    ) {
      return true;
    }
    if (form.getFunding() != null && form.getFunding().stream().anyMatch(this::hasMeaningfulFunding)) {
      return true;
    }
    return form.getAuthors() != null && form.getAuthors().stream().anyMatch(this::hasMeaningfulAuthor);
  }

  private boolean hasMeaningfulArticle(String articleJson) {
    if (!hasText(articleJson)) return false;
    try {
      PaperArticleDto article = objectMapper.readValue(articleJson, PaperArticleDto.class);
      if (article.getSections() == null) return false;
      return article.getSections().stream().anyMatch(section ->
        section != null && section.getBlocks() != null && section.getBlocks().stream().anyMatch(block ->
          block != null && (
            hasText(block.getText()) ||
            hasText(block.getLatex()) ||
            block.getFileId() != null ||
            hasText(block.getLabel()) ||
            hasText(block.getCaption()) ||
            hasText(block.getAltText()) ||
            hasText(block.getSourceNote()) ||
            hasText(block.getNotes()) ||
            hasValues(block.getColumns()) ||
            hasValues(block.getRows())
          )
        )
      );
    } catch (JsonProcessingException error) {
      return true;
    }
  }

  private boolean hasMeaningfulFunding(PaperFundingRequest funding) {
    return funding != null && (hasText(funding.getFunderName()) || hasText(funding.getGrantId()));
  }

  private boolean hasMeaningfulAuthor(PaperAuthorRequest author) {
    if (author == null) return false;
    if (
      hasText(author.getDisplayName()) ||
      hasText(author.getGivenName()) ||
      hasText(author.getMiddleName()) ||
      hasText(author.getFamilyName()) ||
      hasText(author.getEmail()) ||
      hasText(author.getOrcid()) ||
      hasText(author.getInstitutionName()) ||
      hasText(author.getCountry()) ||
      hasValues(author.getContributionRoles())
    ) {
      return true;
    }
    return author.getAffiliations() != null && author.getAffiliations().stream().anyMatch(affiliation ->
      affiliation != null && (
        hasText(affiliation.getOrganizationName()) ||
        hasText(affiliation.getDepartment()) ||
        hasText(affiliation.getAddressLine1()) ||
        hasText(affiliation.getAddressLine2()) ||
        hasText(affiliation.getCountry()) ||
        hasText(affiliation.getRegion()) ||
        hasText(affiliation.getCity()) ||
        hasText(affiliation.getPostalCode())
      )
    );
  }

  private boolean hasText(String value) {
    return value != null && !value.isBlank();
  }

  private boolean hasValues(List<?> values) {
    return values != null && !values.isEmpty();
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
  public PaperSubmissionDraftDto renameDraft(
    String username,
    Long draftId,
    PaperSubmissionDraftRenameRequest request
  ) {
    PaperSubmissionDraft draft = requireOwnedDraft(username, draftId);
    requireEditable(draft);
    draft.setDisplayName(request == null ? null : clean(request.getDisplayName()));
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
    PaperSubmissionValidationDto result = validator.validateDraft(
      readForm(draft.getFormDataJson()),
      fileRepository.findByDraftIdOrderBySortOrderAscIdAsc(draft.getId())
    );
    if (draft.getArticleStatus() != PaperArticleStatus.READY) {
      result.setIssues(new java.util.ArrayList<>(result.getIssues()));
      result.getIssues().add(new com.openisle.dto.PaperSubmissionIssueDto(
        "article-content",
        "article",
        "ARTICLE_CONTENT_NOT_READY",
        "Complete and approve the online article before continuing."
      ));
      result.setValid(false);
    }
    return result;
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
    if (draft.getRevisionSourcePaper() != null) {
      PaperProfile source = draft.getRevisionSourcePaper();
      paper.setRevisionOfPaper(source);
      paper.setRevisionNumber(Math.max(source.getRevisionNumber(), 1) + 1);
      paperProfileRepository.saveAndFlush(paper);
    }
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
    PaperSubmitRequest form = readForm(draft.getFormDataJson());
    List<PaperSubmissionFile> files = fileRepository
      .findByDraftIdOrderBySortOrderAscIdAsc(draft.getId());
    dto.setId(draft.getId());
    dto.setVersion(draft.getVersion());
    dto.setManuscriptType(draft.getManuscriptType());
    dto.setDisplayName(draft.getDisplayName());
    dto.setManuscriptTitle(clean(form.getTitle()));
    dto.setPrimaryManuscriptFileName(
      files.stream()
        .filter(file -> file.getRole() == PaperFileRole.MANUSCRIPT)
        .map(PaperSubmissionFile::getOriginalFileName)
        .filter(this::hasText)
        .findFirst()
        .orElse(null)
    );
    dto.setFileCount(files.size());
    dto.setStale(
      draft.getUpdatedAt() != null &&
      draft.getUpdatedAt().isBefore(LocalDateTime.now().minusDays(STALE_DRAFT_DAYS))
    );
    dto.setCurrentSection(draft.getCurrentSection());
    dto.setStatus(draft.getStatus());
    dto.setFormData(form);
    dto.setFiles(
      files.stream()
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

  private PaperSubmitRequest formFromPaper(PaperProfile paper) {
    PaperSubmitRequest form = new PaperSubmitRequest();
    form.setTitle(paper.getTitle());
    form.setAbstractText(paper.getAbstractText());
    form.setKeywords(lines(paper.getKeywords()));
    form.setReferences(lines(paper.getReferencesText()));
    form.setSubjectArea(paper.getSubjectArea());
    form.setPaperType(paper.getPaperType());
    form.setContent(paper.getPost().getContent());
    form.setPrimaryInstitutionName(
      paper.getPrimaryInstitution() == null ? null : paper.getPrimaryInstitution().getName()
    );
    form.setFundingStatement(paper.getFundingStatement());
    form.setConflictOfInterest(paper.getConflictOfInterest());
    form.setDataAvailability(paper.getDataAvailability());
    form.setEthicsStatement(paper.getEthicsStatement());
    form.setPreprintStatement(paper.getPreprintStatement());
    form.setAiUseDisclosure(paper.getAiUseDisclosure());
    form.setPrivateComments(paper.getPrivateComments());
    form.setAuthors(
      paperAuthorRepository.findByPaperIdOrderByAuthorOrderAsc(paper.getId()).stream()
        .map(this::authorRequestFromPaperAuthor)
        .toList()
    );
    form.setFunding(
      paperFundingRecordRepository.findByPaperIdOrderByDisplayOrderAscIdAsc(paper.getId()).stream()
        .map(record -> {
          PaperFundingRequest funding = new PaperFundingRequest();
          funding.setFunderName(record.getFunderName());
          funding.setGrantId(record.getGrantId());
          return funding;
        })
        .toList()
    );
    form.setNoFundingReceived(form.getFunding().isEmpty());
    return form;
  }

  private PaperAuthorRequest authorRequestFromPaperAuthor(PaperAuthor author) {
    PaperAuthorRequest request = new PaperAuthorRequest();
    request.setDisplayName(author.getDisplayName());
    request.setGivenName(author.getGivenName());
    request.setMiddleName(author.getMiddleName());
    request.setFamilyName(author.getFamilyName());
    request.setEmail(author.getEmail());
    request.setOrcid(author.getOrcid());
    request.setAuthorRole(author.getAuthorRole());
    request.setInstitutionName(author.getInstitution() == null ? null : author.getInstitution().getName());
    request.setCountry(author.getCountry());
    request.setCorrespondingAuthor(author.isCorrespondingAuthor());
    request.setEqualContribution(author.isEqualContribution());
    request.setContributionRoles(lines(author.getContributionRoles()));
    request.setAffiliations(
      paperAuthorAffiliationRepository.findByPaperAuthorIdOrderByDisplayOrderAscIdAsc(author.getId())
        .stream()
        .map(this::affiliationRequestFromPaperAffiliation)
        .toList()
    );
    return request;
  }

  private PaperAffiliationRequest affiliationRequestFromPaperAffiliation(
    PaperAuthorAffiliation affiliation
  ) {
    PaperAffiliationRequest request = new PaperAffiliationRequest();
    request.setOrganizationName(affiliation.getOrganizationName());
    request.setDepartment(affiliation.getDepartment());
    request.setAddressLine1(affiliation.getAddressLine1());
    request.setAddressLine2(affiliation.getAddressLine2());
    request.setCountry(affiliation.getCountry());
    request.setRegion(affiliation.getRegion());
    request.setCity(affiliation.getCity());
    request.setPostalCode(affiliation.getPostalCode());
    request.setPrimaryAffiliation(affiliation.isPrimaryAffiliation());
    return request;
  }

  private Map<Long, Long> copyFilesToRevisionDraft(
    PaperProfile source,
    PaperSubmissionDraft draft
  ) {
    Map<Long, Long> revisionFileIds = new HashMap<>();
    List<PaperFile> sourceFiles = paperFileRepository
      .findByPaperIdOrderBySortOrderAscIdAsc(source.getId());
    List<PaperSubmissionFile> copiedFiles = sourceFiles
      .stream()
      .map(file -> {
        PaperSubmissionFile copy = new PaperSubmissionFile();
        copy.setDraft(draft);
        copy.setOriginalFileName(file.getOriginalFileName());
        copy.setDisplayName(file.getDisplayName());
        copy.setContentType(file.getContentType());
        copy.setFileSize(file.getFileSize());
        copy.setRole(file.getRole());
        copy.setDescription(file.getDescription());
        copy.setVisibility(file.getVisibility());
        copy.setStorageKey(file.getStorageKey());
        copy.setUploadStatus(file.getUploadStatus());
        copy.setSortOrder(file.getSortOrder());
        return copy;
      })
      .toList();
    List<PaperSubmissionFile> savedFiles = fileRepository.saveAllAndFlush(copiedFiles);
    for (int index = 0; index < savedFiles.size(); index++) {
      revisionFileIds.put(
        sourceFiles.get(index).getId(),
        savedFiles.get(index).getId()
      );
    }
    return revisionFileIds;
  }

  private void copyArticleToRevisionDraft(
    PaperProfile source,
    PaperSubmissionDraft draft,
    Map<Long, Long> revisionFileIds
  ) {
    if (source.getArticleJson() == null || source.getArticleJson().isBlank()) {
      draft.setArticleStatus(PaperArticleStatus.NOT_STARTED);
      return;
    }
    try {
      PaperArticleDto article = objectMapper.readValue(source.getArticleJson(), PaperArticleDto.class);
      article.getSections().stream()
        .flatMap(section -> section.getBlocks().stream())
        .filter(block -> "FIGURE".equals(block.getType()) && block.getFileId() != null)
        .forEach(block -> block.setFileId(revisionFileIds.getOrDefault(block.getFileId(), block.getFileId())));
      article.setVersion(1);
      article.setStatus(PaperArticleStatus.IN_PROGRESS);
      article.setReadyAt(null);
      article.setUpdatedAt(null);
      draft.setArticleJson(objectMapper.writeValueAsString(article));
      draft.setArticleVersion(1);
      draft.setArticleStatus(PaperArticleStatus.IN_PROGRESS);
      draft.setArticleReadyAt(null);
    } catch (JsonProcessingException exception) {
      throw new IllegalStateException("Unable to create the revision article", exception);
    }
  }

  private static List<String> lines(String value) {
    return value == null || value.isBlank()
      ? List.of()
      : value.lines().map(String::trim).filter(line -> !line.isBlank()).toList();
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
