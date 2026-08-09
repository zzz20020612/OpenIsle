package com.openisle.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.net.URI;
import java.time.Duration;
import java.util.Set;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

@Service
public class LiteratureIntegrationService {

  private static final Set<String> ALLOWED_SORTS = Set.of(
    "year_desc",
    "year_asc",
    "citations_desc",
    "title_asc"
  );

  private final String baseUrl;
  private final RestTemplate restTemplate;
  private final ObjectMapper objectMapper;

  @Autowired
  public LiteratureIntegrationService(
    @Value("${literature.api-base-url:http://localhost:8088}") String baseUrl,
    @Value("${literature.timeout-seconds:10}") int timeoutSeconds,
    RestTemplateBuilder restTemplateBuilder,
    ObjectMapper objectMapper
  ) {
    this(
      baseUrl,
      restTemplateBuilder
        .setConnectTimeout(Duration.ofSeconds(Math.max(1, timeoutSeconds)))
        .setReadTimeout(Duration.ofSeconds(Math.max(1, timeoutSeconds)))
        .build(),
      objectMapper
    );
  }

  LiteratureIntegrationService(String baseUrl, RestTemplate restTemplate, ObjectMapper objectMapper) {
    this.baseUrl = baseUrl.replaceAll("/+$", "");
    this.restTemplate = restTemplate;
    this.objectMapper = objectMapper;
  }

  public LiteratureProxyResponse health() {
    return get("/health");
  }

  public LiteratureProxyResponse listPapers(
    String query,
    String sort,
    int limit,
    int offset
  ) {
    String safeSort = sort != null && ALLOWED_SORTS.contains(sort) ? sort : "year_desc";
    int safeLimit = Math.max(1, Math.min(limit, 100));
    int safeOffset = Math.max(0, offset);
    UriComponentsBuilder uri = UriComponentsBuilder
      .fromHttpUrl(baseUrl + "/papers/list")
      .queryParam("sort", safeSort)
      .queryParam("limit", safeLimit)
      .queryParam("offset", safeOffset);
    if (query != null && !query.isBlank()) {
      uri.queryParam("q", query.strip());
    }
    return getAbsolute(uri.build().encode().toUriString());
  }

  public LiteratureProxyResponse getPaper(long paperId) {
    return get(paperPath(paperId, ""));
  }

  public LiteratureProxyResponse getKnowledge(long paperId) {
    return get(paperPath(paperId, "/knowledge"));
  }

  public LiteratureProxyResponse getMethods(long paperId) {
    return get(paperPath(paperId, "/methods"));
  }

  public LiteratureProxyResponse getDataPoints(long paperId) {
    return get(paperPath(paperId, "/data_points"));
  }

  private String paperPath(long paperId, String suffix) {
    if (paperId <= 0) {
      throw new IllegalArgumentException("paperId must be positive");
    }
    return "/paper/" + paperId + suffix;
  }

  private LiteratureProxyResponse get(String path) {
    return getAbsolute(baseUrl + path);
  }

  private LiteratureProxyResponse getAbsolute(String url) {
    try {
      ResponseEntity<JsonNode> response = restTemplate.getForEntity(URI.create(url), JsonNode.class);
      JsonNode body = response.getBody() == null ? objectMapper.createObjectNode() : response.getBody();
      return new LiteratureProxyResponse(response.getStatusCode(), body);
    } catch (HttpStatusCodeException ex) {
      if (ex.getStatusCode().value() == HttpStatus.NOT_FOUND.value()) {
        return new LiteratureProxyResponse(HttpStatus.NOT_FOUND, parseErrorBody(ex));
      }
      return error(
        HttpStatus.BAD_GATEWAY,
        "LITERATURE_UPSTREAM_ERROR",
        "The literature service returned an unexpected response."
      );
    } catch (ResourceAccessException ex) {
      return error(
        HttpStatus.SERVICE_UNAVAILABLE,
        "LITERATURE_SERVICE_UNAVAILABLE",
        "The literature knowledge service is not available right now."
      );
    } catch (RuntimeException ex) {
      return error(
        HttpStatus.BAD_GATEWAY,
        "LITERATURE_INVALID_RESPONSE",
        "The literature service returned an invalid response."
      );
    }
  }

  private JsonNode parseErrorBody(HttpStatusCodeException ex) {
    try {
      JsonNode body = objectMapper.readTree(ex.getResponseBodyAsString());
      if (body != null) {
        return body;
      }
    } catch (Exception ignored) {
      // Fall through to the stable local response below.
    }
    ObjectNode body = objectMapper.createObjectNode();
    body.put("code", "LITERATURE_NOT_FOUND");
    body.put("message", "The requested literature record was not found.");
    return body;
  }

  private LiteratureProxyResponse error(HttpStatusCode status, String code, String message) {
    ObjectNode body = objectMapper.createObjectNode();
    body.put("code", code);
    body.put("message", message);
    return new LiteratureProxyResponse(status, body);
  }

  public record LiteratureProxyResponse(HttpStatusCode status, JsonNode body) {}
}
