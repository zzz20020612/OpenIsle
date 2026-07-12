package com.openisle.controller;

import com.openisle.dto.PaperSubmissionDraftDto;
import com.openisle.dto.PaperSubmissionDraftPatchRequest;
import com.openisle.dto.PaperSubmissionValidationDto;
import com.openisle.service.PaperSubmissionDraftService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/paper-submission-drafts")
@RequiredArgsConstructor
@SecurityRequirement(name = "JWT")
@Tag(name = "Paper Submission Drafts", description = "Owner-scoped paper submission workspace APIs")
public class PaperSubmissionDraftController {

  private final PaperSubmissionDraftService draftService;

  @PostMapping
  @Operation(summary = "Create paper submission draft")
  public ResponseEntity<PaperSubmissionDraftDto> createDraft(Authentication authentication) {
    return ResponseEntity.ok(draftService.createDraft(authentication.getName()));
  }

  @GetMapping("/current")
  @Operation(summary = "Restore current paper submission draft")
  @ApiResponse(responseCode = "204", description = "No active submission draft")
  public ResponseEntity<PaperSubmissionDraftDto> getCurrentDraft(Authentication authentication) {
    return draftService
      .getCurrentDraft(authentication.getName())
      .map(ResponseEntity::ok)
      .orElseGet(() -> ResponseEntity.noContent().build());
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
}
