package com.openisle.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.openisle.dto.LiteratureAuthorRankingDto;
import com.openisle.dto.LiteraturePaperRankingDto;
import com.openisle.dto.LiteratureRatingRequest;
import com.openisle.dto.LiteratureRatingResponse;
import com.openisle.dto.LiteratureScoreSnapshotDto;
import com.openisle.service.LiteratureIntegrationService;
import com.openisle.service.LiteratureIntegrationService.LiteratureProxyResponse;
import com.openisle.service.LiteratureRatingService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/literature")
@RequiredArgsConstructor
@Tag(name = "Literature Knowledge and Evaluation", description = "Existing literature, human ratings, and rankings")
public class LiteratureController {

  private final LiteratureIntegrationService literatureService;
  private final LiteratureRatingService literatureRatingService;

  @GetMapping("/health")
  @Operation(summary = "Check literature service availability")
  public ResponseEntity<JsonNode> health() {
    return response(literatureService.health());
  }

  @GetMapping("/papers")
  @Operation(summary = "List existing literature records")
  public ResponseEntity<JsonNode> listPapers(
    @RequestParam(required = false) String q,
    @RequestParam(defaultValue = "year_desc") String sort,
    @RequestParam(defaultValue = "30") int limit,
    @RequestParam(defaultValue = "0") int offset
  ) {
    return response(literatureService.listPapers(q, sort, limit, offset));
  }

  @GetMapping("/papers/{paperId}")
  @Operation(summary = "Get a literature record")
  public ResponseEntity<JsonNode> getPaper(@PathVariable long paperId) {
    return response(literatureService.getPaper(paperId));
  }

  @GetMapping("/papers/{paperId}/knowledge")
  @Operation(summary = "Get an extracted knowledge card")
  public ResponseEntity<JsonNode> getKnowledge(@PathVariable long paperId) {
    return response(literatureService.getKnowledge(paperId));
  }

  @GetMapping("/papers/{paperId}/methods")
  @Operation(summary = "Get extracted methods")
  public ResponseEntity<JsonNode> getMethods(@PathVariable long paperId) {
    return response(literatureService.getMethods(paperId));
  }

  @GetMapping("/papers/{paperId}/data-points")
  @Operation(summary = "Get extracted data points")
  public ResponseEntity<JsonNode> getDataPoints(@PathVariable long paperId) {
    return response(literatureService.getDataPoints(paperId));
  }

  @PostMapping("/papers/{paperId}/ratings")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Rate an existing literature paper", description = "Create or update the current user's six-dimensional rating.")
  public LiteratureRatingResponse ratePaper(
    @PathVariable Long paperId,
    @RequestBody LiteratureRatingRequest request,
    Authentication authentication
  ) {
    return literatureRatingService.rateLiterature(authentication.getName(), paperId, request);
  }

  @GetMapping("/papers/{paperId}/ratings")
  @Operation(summary = "List ratings for an existing literature paper")
  public List<LiteratureRatingResponse> listRatings(@PathVariable Long paperId) {
    return literatureRatingService.listRatings(paperId);
  }

  @GetMapping("/papers/{paperId}/ratings/me")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Get the current user's literature rating")
  public LiteratureRatingResponse getMyRating(
    @PathVariable Long paperId,
    Authentication authentication
  ) {
    return literatureRatingService.getMyRating(authentication.getName(), paperId);
  }

  @GetMapping("/papers/{paperId}/score")
  @Operation(summary = "Get a literature paper's six-dimensional score snapshot")
  public LiteratureScoreSnapshotDto getScore(@PathVariable Long paperId) {
    return literatureRatingService.getScoreSnapshot(paperId);
  }

  @GetMapping("/rankings/papers")
  @Operation(summary = "Rank rated existing literature papers")
  public List<LiteraturePaperRankingDto> rankPapers(@RequestParam(defaultValue = "50") int limit) {
    return literatureRatingService.rankPapers(limit);
  }

  @GetMapping("/rankings/authors")
  @Operation(summary = "Rank authors from rated existing literature papers")
  public List<LiteratureAuthorRankingDto> rankAuthors(@RequestParam(defaultValue = "50") int limit) {
    return literatureRatingService.rankAuthors(limit);
  }

  private ResponseEntity<JsonNode> response(LiteratureProxyResponse response) {
    return ResponseEntity.status(response.status()).body(response.body());
  }
}
