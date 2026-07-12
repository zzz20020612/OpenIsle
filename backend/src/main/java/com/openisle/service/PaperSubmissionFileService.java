package com.openisle.service;

import com.openisle.dto.PaperSubmissionFileDto;
import com.openisle.dto.PaperSubmissionFilePresignRequest;
import com.openisle.dto.PaperSubmissionFilePresignResponse;
import com.openisle.dto.PaperSubmissionFileUpdateRequest;
import com.openisle.exception.NotFoundException;
import com.openisle.model.PaperSubmissionDraft;
import com.openisle.model.PaperSubmissionDraftStatus;
import com.openisle.model.PaperSubmissionFile;
import com.openisle.model.PaperUploadStatus;
import com.openisle.repository.PaperSubmissionFileRepository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class PaperSubmissionFileService {

  private final PaperSubmissionDraftService draftService;
  private final PaperSubmissionFileRepository fileRepository;
  private final PaperFilePolicy filePolicy;
  private final PresignedFileStorageService storageService;

  @Transactional
  public PaperSubmissionFilePresignResponse presign(
    String username,
    Long draftId,
    PaperSubmissionFilePresignRequest request
  ) {
    PaperSubmissionDraft draft = requireEditableDraft(username, draftId);
    filePolicy.validate(request);
    Map<String, String> upload = storageService.presignUpload(
      request.getFileName(),
      filePolicy.storagePurpose(request.getRole())
    );
    String key = upload.get("key");
    String uploadUrl = upload.get("uploadUrl");
    if (key == null || uploadUrl == null) {
      throw new IllegalStateException("Storage provider returned an incomplete upload response");
    }

    int sortOrder = fileRepository
      .findByDraftIdOrderBySortOrderAscIdAsc(draftId)
      .stream()
      .mapToInt(PaperSubmissionFile::getSortOrder)
      .max()
      .orElse(-1) + 1;

    PaperSubmissionFile file = new PaperSubmissionFile();
    file.setDraft(draft);
    file.setOriginalFileName(request.getFileName().trim());
    file.setDisplayName(
      clean(request.getDisplayName()) != null
        ? clean(request.getDisplayName())
        : request.getFileName().trim()
    );
    file.setContentType(
      clean(request.getContentType()) != null
        ? clean(request.getContentType())
        : "application/octet-stream"
    );
    file.setFileSize(request.getFileSize());
    file.setRole(request.getRole());
    file.setDescription(clean(request.getDescription()));
    file.setVisibility(filePolicy.resolveVisibility(request.getRole(), request.getVisibility()));
    file.setStorageKey(key);
    file.setUploadStatus(PaperUploadStatus.PENDING);
    file.setSortOrder(sortOrder);
    file = fileRepository.saveAndFlush(file);

    PaperSubmissionFilePresignResponse response = new PaperSubmissionFilePresignResponse();
    response.setFileId(file.getId());
    response.setUploadUrl(uploadUrl);
    response.setUploadHeaders(Map.of());
    response.setExpiresAt(LocalDateTime.now().plusMinutes(15));
    response.setFile(toDto(file));
    return response;
  }

  @Transactional
  public PaperSubmissionFileDto updateFile(
    String username,
    Long draftId,
    Long fileId,
    PaperSubmissionFileUpdateRequest request
  ) {
    requireEditableDraft(username, draftId);
    PaperSubmissionFile file = requireFile(draftId, fileId);
    if (request == null) {
      return toDto(file);
    }
    var targetRole = request.getRole() != null ? request.getRole() : file.getRole();
    var targetDescription = request.getDescription() != null
      ? clean(request.getDescription())
      : file.getDescription();
    var targetVisibility = request.getVisibility() != null
      ? request.getVisibility()
      : file.getVisibility();
    PaperSubmissionFilePresignRequest validation = new PaperSubmissionFilePresignRequest();
    validation.setFileName(file.getOriginalFileName());
    validation.setFileSize(file.getFileSize());
    validation.setRole(targetRole);
    validation.setDescription(targetDescription);
    validation.setVisibility(targetVisibility);
    filePolicy.validate(validation);

    if (clean(request.getDisplayName()) != null) {
      file.setDisplayName(clean(request.getDisplayName()));
    }
    file.setRole(targetRole);
    if (request.getDescription() != null) {
      file.setDescription(targetDescription);
    }
    if (request.getVisibility() != null || request.getRole() != null) {
      file.setVisibility(
        filePolicy.resolveVisibility(targetRole, targetVisibility)
      );
    }
    if (request.getUploadStatus() != null) {
      file.setUploadStatus(request.getUploadStatus());
    }
    if (request.getSortOrder() != null && request.getSortOrder() >= 0) {
      file.setSortOrder(request.getSortOrder());
    }
    return toDto(fileRepository.saveAndFlush(file));
  }

  @Transactional
  public void deleteFile(String username, Long draftId, Long fileId) {
    requireEditableDraft(username, draftId);
    fileRepository.delete(requireFile(draftId, fileId));
  }

  @Transactional(readOnly = true)
  public List<PaperSubmissionFileDto> listFiles(String username, Long draftId) {
    draftService.requireOwnedDraft(username, draftId);
    return fileRepository
      .findByDraftIdOrderBySortOrderAscIdAsc(draftId)
      .stream()
      .map(this::toDto)
      .toList();
  }

  @Transactional(readOnly = true)
  public String getContentUrl(
    String username,
    Long draftId,
    Long fileId,
    boolean inline
  ) {
    draftService.requireOwnedDraft(username, draftId);
    PaperSubmissionFile file = requireFile(draftId, fileId);
    if (file.getUploadStatus() != PaperUploadStatus.UPLOADED) {
      throw new IllegalStateException("The file upload is not complete");
    }
    return storageService.presignDownload(
      file.getStorageKey(),
      file.getDisplayName(),
      inline
    );
  }

  private PaperSubmissionDraft requireEditableDraft(String username, Long draftId) {
    PaperSubmissionDraft draft = draftService.requireOwnedDraft(username, draftId);
    if (draft.getStatus() != PaperSubmissionDraftStatus.IN_PROGRESS) {
      throw new IllegalStateException("This submission draft is no longer editable");
    }
    return draft;
  }

  private PaperSubmissionFile requireFile(Long draftId, Long fileId) {
    return fileRepository
      .findByIdAndDraftId(fileId, draftId)
      .orElseThrow(() -> new NotFoundException("Submission file not found"));
  }

  private PaperSubmissionFileDto toDto(PaperSubmissionFile file) {
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

  private static String clean(String value) {
    return value == null || value.isBlank() ? null : value.trim();
  }
}
