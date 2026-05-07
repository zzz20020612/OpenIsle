package com.openisle.controller;

import com.openisle.dto.AuthorRankingDto;
import com.openisle.dto.InstitutionRankingDto;
import com.openisle.dto.PaperDetailDto;
import com.openisle.dto.PaperFilterOptionsDto;
import com.openisle.dto.PaperRankingDto;
import com.openisle.dto.PaperRatingRequest;
import com.openisle.dto.PaperRatingResponse;
import com.openisle.dto.PaperScoreSnapshotDto;
import com.openisle.dto.PaperSubmitRequest;
import com.openisle.dto.PaperSummaryDto;
import com.openisle.service.PaperRatingService;
import com.openisle.service.PaperRankingService;
import com.openisle.service.PaperService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/papers")
@RequiredArgsConstructor
@Tag(name = "Papers", description = "Paper submission and publication APIs")
public class PaperController {

  private final PaperService paperService;
  private final PaperRatingService paperRatingService;
  private final PaperRankingService paperRankingService;

  @PostMapping
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Submit paper", description = "Create a paper and run MVP AI screening.")
  public ResponseEntity<PaperDetailDto> submitPaper(
    @RequestBody PaperSubmitRequest request,
    Authentication authentication
  ) {
    return ResponseEntity.ok(paperService.submitPaper(authentication.getName(), request));
  }

  @GetMapping
  @Operation(summary = "List published papers", description = "Return public paper feed.")
  public List<PaperSummaryDto> listPapers(
    @RequestParam(value = "page", defaultValue = "0") int page,
    @RequestParam(value = "pageSize", defaultValue = "20") int pageSize,
    @RequestParam(value = "subject", required = false) String subject,
    @RequestParam(value = "minScore", required = false) Double minScore,
    @RequestParam(value = "sort", defaultValue = "latest") String sort
  ) {
    return paperService.listPublishedPapers(page, pageSize, subject, minScore, sort);
  }

  @GetMapping("/filters")
  @Operation(summary = "Get paper filter options", description = "Return subject filters for the paper feed.")
  public PaperFilterOptionsDto getPaperFilters() {
    return paperService.getFilterOptions();
  }

  @GetMapping("/rankings/top-rated")
  @Operation(summary = "List top rated papers", description = "Return papers ranked by composite score.")
  public List<PaperRankingDto> listTopRatedPapers(
    @RequestParam(value = "limit", defaultValue = "20") int limit
  ) {
    return paperRankingService.listTopPapers(limit);
  }

  @GetMapping("/rankings/authors")
  @Operation(summary = "List author rankings", description = "Return authors ranked by paper score history.")
  public List<AuthorRankingDto> listAuthorRankings(
    @RequestParam(value = "limit", defaultValue = "20") int limit
  ) {
    return paperRankingService.listAuthorRankings(limit);
  }

  @GetMapping("/rankings/institutions")
  @Operation(
    summary = "List institution rankings",
    description = "Return institutions ranked by associated paper score history."
  )
  public List<InstitutionRankingDto> listInstitutionRankings(
    @RequestParam(value = "limit", defaultValue = "20") int limit
  ) {
    return paperRankingService.listInstitutionRankings(limit);
  }

  @GetMapping("/{paperId}")
  @Operation(summary = "Get paper detail", description = "Return paper metadata and full text.")
  public PaperDetailDto getPaper(@PathVariable Long paperId, Authentication authentication) {
    String viewer = authentication != null ? authentication.getName() : null;
    return paperService.getPaper(paperId, viewer);
  }

  @PostMapping("/{paperId}/ratings")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Rate paper", description = "Create or update the current user's paper rating.")
  public ResponseEntity<PaperRatingResponse> ratePaper(
    @PathVariable Long paperId,
    @RequestBody PaperRatingRequest request,
    Authentication authentication
  ) {
    return ResponseEntity.ok(paperRatingService.ratePaper(authentication.getName(), paperId, request));
  }

  @GetMapping("/{paperId}/ratings/me")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Get my paper rating", description = "Return the current user's rating for a paper.")
  public PaperRatingResponse getMyRating(
    @PathVariable Long paperId,
    Authentication authentication
  ) {
    return paperRatingService.getMyRating(authentication.getName(), paperId);
  }

  @GetMapping("/{paperId}/score")
  @Operation(summary = "Get paper score", description = "Return the current aggregated score snapshot.")
  public PaperScoreSnapshotDto getPaperScore(@PathVariable Long paperId) {
    return paperRatingService.getScoreSnapshot(paperId);
  }
}
