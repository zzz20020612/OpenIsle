package com.openisle.controller;

import com.openisle.dto.PaperSubmissionDraftDto;
import com.openisle.dto.PaperSubmissionDraftPatchRequest;
import com.openisle.dto.PaperSubmissionDraftRenameRequest;
import com.openisle.dto.PaperSubmissionFileDto;
import com.openisle.dto.PaperSubmissionFilePresignRequest;
import com.openisle.dto.PaperSubmissionFilePresignResponse;
import com.openisle.dto.PaperSubmissionFileUpdateRequest;
import com.openisle.dto.PaperSubmissionResultDto;
import com.openisle.dto.PaperSubmissionSubmitRequest;
import com.openisle.dto.PaperSubmissionValidationDto;
import com.openisle.model.PaperSubmissionDraftKind;
import com.openisle.service.PaperSubmissionDraftService;
import com.openisle.service.PaperSubmissionFileService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import jakarta.validation.Valid;
import java.net.URI;
import java.util.List;
import org.springframework.http.CacheControl;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/paper-submission-drafts")
@RequiredArgsConstructor
@SecurityRequirement(name = "JWT")
@Tag(name = "Paper Submission Drafts", description = "Owner-scoped paper submission workspace APIs")
public class PaperSubmissionDraftController {

  private final PaperSubmissionDraftService draftService;
  private final PaperSubmissionFileService fileService;

  @PostMapping
  @Operation(summary = "Create paper submission draft")
  public ResponseEntity<PaperSubmissionDraftDto> createDraft(Authentication authentication) {
    return ResponseEntity.ok(draftService.createDraft(authentication.getName()));
  }

  @PostMapping("/revisions/{paperId}")
  @Operation(summary = "Create a revision draft from a revision-needed paper")
  public ResponseEntity<PaperSubmissionDraftDto> createRevisionDraft(
    @PathVariable Long paperId,
    Authentication authentication
  ) {
    return ResponseEntity.ok(draftService.createRevisionDraft(authentication.getName(), paperId));
  }

  @GetMapping("/current")
  @Operation(summary = "Restore current paper submission draft")
  @ApiResponse(responseCode = "204", description = "No active submission draft")
  public ResponseEntity<PaperSubmissionDraftDto> getCurrentDraft(
    @RequestParam(defaultValue = "ANY") PaperSubmissionDraftKind kind,
    Authentication authentication
  ) {
    return draftService
      .getCurrentDraft(authentication.getName(), kind)
      .map(ResponseEntity::ok)
      .orElseGet(() -> ResponseEntity.noContent().build());
  }

  @GetMapping
  @Operation(summary = "List active paper submission drafts")
  public List<PaperSubmissionDraftDto> listDrafts(
    @RequestParam(defaultValue = "ANY") PaperSubmissionDraftKind kind,
    Authentication authentication
  ) {
    return draftService.listDrafts(authentication.getName(), kind);
  }

  @GetMapping("/{draftId}")
  @Operation(summary = "Get paper submission draft")
  public PaperSubmissionDraftDto getDraft(
    @PathVariable Long draftId,
    Authentication authentication
  ) {
    return draftService.getDraft(authentication.getName(), draftId);
  }

  @PatchMapping("/{draftId}")
  @Operation(summary = "Autosave paper submission draft")
  @ApiResponse(responseCode = "409", description = "Draft version conflict")
  public PaperSubmissionDraftDto updateDraft(
    @PathVariable Long draftId,
    @RequestBody PaperSubmissionDraftPatchRequest request,
    Authentication authentication
  ) {
    return draftService.updateDraft(authentication.getName(), draftId, request);
  }

  @PatchMapping("/{draftId}/name")
  @Operation(summary = "Rename paper submission draft")
  public PaperSubmissionDraftDto renameDraft(
    @PathVariable Long draftId,
    @Valid @RequestBody PaperSubmissionDraftRenameRequest request,
    Authentication authentication
  ) {
    return draftService.renameDraft(authentication.getName(), draftId, request);
  }

  @DeleteMapping("/{draftId}")
  @Operation(summary = "Discard paper submission draft")
  public ResponseEntity<Void> discardDraft(
    @PathVariable Long draftId,
    Authentication authentication
  ) {
    draftService.discardDraft(authentication.getName(), draftId);
    return ResponseEntity.noContent().build();
  }

  @PostMapping("/{draftId}/validate")
  @Operation(summary = "Validate paper submission draft")
  public PaperSubmissionValidationDto validateDraft(
    @PathVariable Long draftId,
    Authentication authentication
  ) {
    return draftService.validateDraft(authentication.getName(), draftId);
  }

  @PostMapping("/{draftId}/submit")
  @Operation(summary = "Finalize a paper submission draft")
  @ApiResponse(responseCode = "200", description = "Draft finalized or prior result returned")
  public PaperSubmissionResultDto submitDraft(
    @PathVariable Long draftId,
    @RequestBody PaperSubmissionSubmitRequest request,
    Authentication authentication
  ) {
    return draftService.submitDraft(authentication.getName(), draftId, request);
  }

  @GetMapping("/{draftId}/files")
  @Operation(summary = "List paper submission draft files")
  public List<PaperSubmissionFileDto> listFiles(
    @PathVariable Long draftId,
    Authentication authentication
  ) {
    return fileService.listFiles(authentication.getName(), draftId);
  }

  @PostMapping("/{draftId}/files/presign")
  @Operation(summary = "Create draft-scoped presigned upload")
  public PaperSubmissionFilePresignResponse presignFile(
    @PathVariable Long draftId,
    @RequestBody PaperSubmissionFilePresignRequest request,
    Authentication authentication
  ) {
    return fileService.presign(authentication.getName(), draftId, request);
  }

  @PatchMapping("/{draftId}/files/{fileId}")
  @Operation(summary = "Update paper submission file metadata")
  public PaperSubmissionFileDto updateFile(
    @PathVariable Long draftId,
    @PathVariable Long fileId,
    @RequestBody PaperSubmissionFileUpdateRequest request,
    Authentication authentication
  ) {
    return fileService.updateFile(authentication.getName(), draftId, fileId, request);
  }

  @DeleteMapping("/{draftId}/files/{fileId}")
  @Operation(summary = "Remove paper submission file")
  public ResponseEntity<Void> deleteFile(
    @PathVariable Long draftId,
    @PathVariable Long fileId,
    Authentication authentication
  ) {
    fileService.deleteFile(authentication.getName(), draftId, fileId);
    return ResponseEntity.noContent().build();
  }

  @GetMapping("/{draftId}/files/{fileId}/content")
  @Operation(summary = "Open a paper submission file through a signed URL")
  public ResponseEntity<Void> openFile(
    @PathVariable Long draftId,
    @PathVariable Long fileId,
    @RequestParam(defaultValue = "true") boolean inline,
    Authentication authentication
  ) {
    String url = fileService.getContentUrl(
      authentication.getName(),
      draftId,
      fileId,
      inline
    );
    return ResponseEntity
      .status(HttpStatus.FOUND)
      .location(URI.create(url))
      .cacheControl(CacheControl.noStore())
      .build();
  }
}
