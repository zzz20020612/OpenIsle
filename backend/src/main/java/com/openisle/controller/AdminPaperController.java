package com.openisle.controller;

import com.openisle.dto.PaperAdminSummaryDto;
import com.openisle.model.PaperPublicationStatus;
import com.openisle.service.PaperAdminService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/admin/papers")
@RequiredArgsConstructor
@SecurityRequirement(name = "JWT")
@Tag(name = "Admin Papers", description = "Admin paper operations built on linked OpenIsle posts")
public class AdminPaperController {

  private final PaperAdminService paperAdminService;

  @GetMapping
  @Operation(summary = "List all papers", description = "Return papers across publication statuses.")
  public List<PaperAdminSummaryDto> listPapers(
    @RequestParam(value = "page", defaultValue = "0") int page,
    @RequestParam(value = "pageSize", defaultValue = "30") int pageSize,
    @RequestParam(value = "status", required = false) PaperPublicationStatus status
  ) {
    return paperAdminService.listPapers(page, pageSize, status);
  }

  @GetMapping("/{paperId}")
  @Operation(summary = "Get admin paper detail", description = "Return an admin paper management record.")
  public PaperAdminSummaryDto getPaper(@PathVariable Long paperId) {
    return paperAdminService.getPaper(paperId);
  }

  @PostMapping("/{paperId}/retract")
  @Operation(summary = "Retract paper", description = "Retract paper and hide its linked post.")
  public PaperAdminSummaryDto retractPaper(@PathVariable Long paperId) {
    return paperAdminService.retractPaper(paperId);
  }

  @PostMapping("/{paperId}/retry-screening")
  @Operation(summary = "Retry AI screening", description = "Retry a failed paper screening.")
  public PaperAdminSummaryDto retryScreening(@PathVariable Long paperId) {
    return paperAdminService.retryScreening(paperId);
  }

  @PostMapping("/{paperId}/publish")
  @Operation(
    summary = "Publish paper after editorial review",
    description = "Publish a paper that AI screening recommended for revision while preserving its screening result."
  )
  public PaperAdminSummaryDto publishPaper(@PathVariable Long paperId) {
    return paperAdminService.publishPaper(paperId);
  }
}
