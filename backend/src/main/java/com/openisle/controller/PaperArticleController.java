package com.openisle.controller;

import com.openisle.dto.PaperArticleDto;
import com.openisle.dto.PaperArticleValidationDto;
import com.openisle.service.PaperArticleService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequiredArgsConstructor
@Tag(name = "Paper Articles", description = "Structured article editor and publication content APIs")
public class PaperArticleController {

  private final PaperArticleService articleService;

  @GetMapping("/api/paper-submission-drafts/{draftId}/article")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Get structured draft article")
  public PaperArticleDto getDraft(@PathVariable Long draftId, Authentication authentication) {
    return articleService.getDraftArticle(authentication.getName(), draftId);
  }

  @PutMapping("/api/paper-submission-drafts/{draftId}/article")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Autosave structured draft article")
  public PaperArticleDto updateDraft(
    @PathVariable Long draftId,
    @RequestBody PaperArticleDto request,
    Authentication authentication
  ) {
    return articleService.updateDraftArticle(authentication.getName(), draftId, request);
  }

  @PostMapping("/api/paper-submission-drafts/{draftId}/article/validate")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Validate structured draft article")
  public PaperArticleValidationDto validate(
    @PathVariable Long draftId,
    Authentication authentication
  ) {
    return articleService.validateDraftArticle(authentication.getName(), draftId);
  }

  @PostMapping("/api/paper-submission-drafts/{draftId}/article/ready")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Mark structured article ready")
  public PaperArticleDto ready(
    @PathVariable Long draftId,
    @RequestBody PaperArticleDto request,
    Authentication authentication
  ) {
    return articleService.markReady(authentication.getName(), draftId, request);
  }

  @PostMapping("/api/paper-submission-drafts/{draftId}/article/reopen")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Reopen structured draft article")
  public PaperArticleDto reopen(@PathVariable Long draftId, Authentication authentication) {
    return articleService.reopen(authentication.getName(), draftId);
  }

  @GetMapping("/api/papers/{paperId}/article")
  @Operation(summary = "Get published structured article")
  public PaperArticleDto getPublished(@PathVariable Long paperId, Authentication authentication) {
    String viewer = authentication != null ? authentication.getName() : null;
    return articleService.getPublishedArticle(paperId, viewer);
  }
}
