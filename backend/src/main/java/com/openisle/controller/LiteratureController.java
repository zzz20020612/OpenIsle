package com.openisle.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.openisle.dto.LiteratureAuthorRankingDto;
import com.openisle.dto.LiteraturePaperRankingDto;
import com.openisle.dto.LiteratureRatingRequest;
import com.openisle.dto.LiteratureRatingResponse;
import com.openisle.dto.LiteratureScoreSnapshotDto;
import com.openisle.dto.LiteratureConflictDeclarationRequest;
import com.openisle.dto.LiteratureReviewTaskDto;
import com.openisle.dto.LiteratureReviewerProfileDto;
import com.openisle.service.LiteratureIntegrationService;
import com.openisle.service.LiteratureAdminAuditService;
import com.openisle.service.LiteratureIntegrationService.LiteratureProxyResponse;
import com.openisle.service.LiteratureIntegrationService.LiteratureFileResponse;
import com.openisle.service.LiteratureRatingService;
import com.openisle.service.LiteratureReviewTaskService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.List;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/literature")
@RequiredArgsConstructor
@Tag(name = "Literature Knowledge and Evaluation", description = "Existing literature, human ratings, and rankings")
public class LiteratureController {

  private final LiteratureIntegrationService literatureService;
  private final LiteratureRatingService literatureRatingService;
  private final LiteratureAdminAuditService literatureAdminAuditService;
  private final LiteratureReviewTaskService literatureReviewTaskService;

  @GetMapping("/health")
  @Operation(summary = "Check literature service availability")
  public ResponseEntity<JsonNode> health() {
    return response(literatureService.health());
  }

  @GetMapping("/capabilities")
  @Operation(summary = "Inspect the literature engine's effective runtime capabilities")
  public ResponseEntity<JsonNode> capabilities() {
    return response(literatureService.capabilities());
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

  @GetMapping("/papers/{paperId}/pdf")
  @Operation(summary = "View an available open literature PDF")
  public ResponseEntity<byte[]> viewPdf(@PathVariable long paperId) {
    return pdfResponse(literatureService.getPdf(paperId), paperId, false);
  }

  @GetMapping("/papers/{paperId}/pdf/download")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Download an available literature PDF", description = "Registration is required.")
  public ResponseEntity<byte[]> downloadPdf(@PathVariable long paperId) {
    return pdfResponse(literatureService.getPdf(paperId), paperId, true);
  }

  @GetMapping("/papers/{paperId}/figures/{figureId}")
  @Operation(summary = "View an extracted literature figure")
  public ResponseEntity<byte[]> viewFigure(@PathVariable long paperId, @PathVariable long figureId) {
    LiteratureFileResponse result = literatureService.getFigure(paperId, figureId);
    ResponseEntity.BodyBuilder response = ResponseEntity.status(result.status());
    response.contentType(result.contentType() == null ? MediaType.APPLICATION_OCTET_STREAM : result.contentType());
    if (result.status().is2xxSuccessful()) {
      response.header("Cache-Control", "public, max-age=86400");
      response.header("X-Content-Type-Options", "nosniff");
    }
    return response.body(result.body());
  }

  @RequestMapping(value = "/explore/**", method = RequestMethod.GET)
  @Operation(summary = "Use the complete public literature discovery API")
  public ResponseEntity<JsonNode> explore(HttpServletRequest request) {
    String path = suffix(request.getRequestURI(), "/api/literature/explore");
    return response(literatureService.publicGet(path, request.getQueryString()));
  }

  @RequestMapping(value = "/admin/**", method = { RequestMethod.GET, RequestMethod.POST })
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Run an audited literature processing operation", description = "Administrator only.")
  public ResponseEntity<JsonNode> administer(
    @RequestBody(required = false) JsonNode body,
    Authentication authentication,
    HttpServletRequest request
  ) {
    String path = suffix(request.getRequestURI(), "/api/literature/admin");
    LiteratureProxyResponse result = literatureService.admin(request.getMethod(), path, request.getQueryString(), body);
    literatureAdminAuditService.record(
      authentication.getName(), request.getMethod(), path, body, result.status().value(), request.getRemoteAddr()
    );
    return response(result);
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

  @GetMapping("/review-tasks/available")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "List complete literature records available to claim for review")
  public List<LiteratureReviewTaskDto> availableReviewTasks(
    @RequestParam(defaultValue = "20") int limit,
    Authentication authentication
  ) {
    return literatureReviewTaskService.available(authentication.getName(), limit);
  }

  @GetMapping("/review-tasks/mine")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "List the current reviewer's accepted and completed tasks")
  public List<LiteratureReviewTaskDto> myReviewTasks(Authentication authentication) {
    return literatureReviewTaskService.mine(authentication.getName());
  }

  @GetMapping("/review-tasks/profile")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Get reviewer points, level, credit, and qualification")
  public LiteratureReviewerProfileDto myReviewerProfile(Authentication authentication) {
    return literatureReviewTaskService.myProfile(authentication.getName());
  }

  @PostMapping("/review-tasks/{paperId}/claim")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Declare conflicts and claim an existing-literature review task")
  public LiteratureReviewTaskDto claimReviewTask(
    @PathVariable Long paperId,
    @RequestBody LiteratureConflictDeclarationRequest declaration,
    Authentication authentication
  ) {
    return literatureReviewTaskService.claim(authentication.getName(), paperId, declaration);
  }

  private ResponseEntity<JsonNode> response(LiteratureProxyResponse response) {
    return ResponseEntity.status(response.status()).body(response.body());
  }

  private String suffix(String uri, String marker) {
    int index = uri.indexOf(marker);
    return index < 0 ? "/" : uri.substring(index + marker.length());
  }

  private ResponseEntity<byte[]> pdfResponse(LiteratureFileResponse result, long paperId, boolean download) {
    MediaType type = result.contentType() == null ? MediaType.APPLICATION_PDF : result.contentType();
    ResponseEntity.BodyBuilder response = ResponseEntity.status(result.status()).contentType(type);
    if (result.status().is2xxSuccessful()) {
      response.header(HttpHeaders.CONTENT_DISPOSITION, (download ? "attachment" : "inline") + "; filename=\"literature-" + paperId + ".pdf\"");
      response.header("X-Content-Type-Options", "nosniff");
    }
    return response.body(result.body());
  }
}
