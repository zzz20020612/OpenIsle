package com.openisle.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.openisle.service.LiteratureIntegrationService;
import com.openisle.service.LiteratureIntegrationService.LiteratureProxyResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/literature")
@RequiredArgsConstructor
@Tag(name = "Literature Knowledge Base", description = "Read-only access to the literature knowledge service")
public class LiteratureController {

  private final LiteratureIntegrationService literatureService;

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

  private ResponseEntity<JsonNode> response(LiteratureProxyResponse response) {
    return ResponseEntity.status(response.status()).body(response.body());
  }
}
