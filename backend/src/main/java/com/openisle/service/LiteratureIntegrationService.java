package com.openisle.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.net.URI;
import java.time.Duration;
import java.util.Map;
import java.util.Set;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
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
  private final RestTemplate pdfRestTemplate;
  private final ObjectMapper objectMapper;
  private final String internalToken;

  private static final Set<String> PUBLIC_PATHS = Set.of(
    "/search", "/aggregate", "/vector/search", "/vector/stats", "/hybrid/search",
    "/graph", "/graph/diagnostics", "/papers/list", "/data_points/list", "/knowledge/list", "/methods/list",
    "/timeline", "/compare/metric", "/authors/list", "/institution/network", "/stats"
  );

  private static final Set<String> ADMIN_PATHS = Set.of(
    "/stats", "/jobs", "/jobs/stats", "/workflow/settings",
    "/quality/stats", "/quality/low_quality", "/quality/prompt_compare", "/rebuild",
    "/sync", "/collect", "/parse", "/extract", "/jobs/archive", "/retry",
    "/quality/re_extract", "/authors/merge", "/test/connection", "/pipeline/run"
  );

  @Autowired
  public LiteratureIntegrationService(
    @Value("${literature.api-base-url:http://localhost:8088}") String baseUrl,
    @Value("${literature.timeout-seconds:10}") int timeoutSeconds,
    @Value("${literature.pdf-parse-timeout-seconds:600}") int pdfParseTimeoutSeconds,
    @Value("${literature.internal-token:}") String internalToken,
    RestTemplateBuilder restTemplateBuilder,
    ObjectMapper objectMapper
  ) {
    this(
      baseUrl,
      restTemplateBuilder
        .setConnectTimeout(Duration.ofSeconds(Math.max(1, timeoutSeconds)))
        .setReadTimeout(Duration.ofSeconds(Math.max(1, timeoutSeconds)))
        .build(),
      restTemplateBuilder
        .setConnectTimeout(Duration.ofSeconds(Math.max(1, timeoutSeconds)))
        .setReadTimeout(Duration.ofSeconds(Math.max(1, pdfParseTimeoutSeconds)))
        .build(),
      objectMapper,
      internalToken
    );
  }

  LiteratureIntegrationService(String baseUrl, RestTemplate restTemplate, ObjectMapper objectMapper) {
    this(baseUrl, restTemplate, restTemplate, objectMapper, "");
  }

  LiteratureIntegrationService(String baseUrl, RestTemplate restTemplate, ObjectMapper objectMapper, String internalToken) {
    this(baseUrl, restTemplate, restTemplate, objectMapper, internalToken);
  }

  LiteratureIntegrationService(
    String baseUrl,
    RestTemplate restTemplate,
    RestTemplate pdfRestTemplate,
    ObjectMapper objectMapper,
    String internalToken
  ) {
    this.baseUrl = baseUrl.replaceAll("/+$", "");
    this.restTemplate = restTemplate;
    this.pdfRestTemplate = pdfRestTemplate;
    this.objectMapper = objectMapper;
    this.internalToken = internalToken == null ? "" : internalToken.strip();
  }

  public LiteratureProxyResponse health() {
    return get("/health");
  }

  public LiteratureProxyResponse capabilities() {
    return get("/capabilities");
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

  public LiteratureFileResponse getPdf(long paperId) {
    if (paperId <= 0) throw new IllegalArgumentException("paperId must be positive");
    try {
      ResponseEntity<byte[]> response = restTemplate.getForEntity(URI.create(baseUrl + "/paper/" + paperId + "/pdf"), byte[].class);
      return new LiteratureFileResponse(response.getStatusCode(), response.getBody(), response.getHeaders().getContentType());
    } catch (HttpStatusCodeException ex) {
      return new LiteratureFileResponse(ex.getStatusCode(), ex.getResponseBodyAsByteArray(), MediaType.APPLICATION_JSON);
    } catch (ResourceAccessException ex) {
      return new LiteratureFileResponse(HttpStatus.SERVICE_UNAVAILABLE, new byte[0], MediaType.APPLICATION_JSON);
    }
  }

  public LiteratureProxyResponse parseSubmissionPdf(byte[] pdfBytes) {
    if (pdfBytes == null || pdfBytes.length < 5) {
      throw new IllegalArgumentException("PDF file is empty");
    }
    if (internalToken.isBlank()) {
      return error(HttpStatus.SERVICE_UNAVAILABLE, "PDF_PARSER_NOT_CONFIGURED", "The PDF parsing service is not configured.");
    }
    HttpHeaders headers = new HttpHeaders();
    headers.set("X-OpenIsle-Internal-Token", internalToken);
    headers.setContentType(MediaType.APPLICATION_PDF);
    try {
      ResponseEntity<JsonNode> response = pdfRestTemplate.exchange(
        URI.create(baseUrl + "/submission/parse-pdf"),
        HttpMethod.POST,
        new HttpEntity<>(pdfBytes, headers),
        JsonNode.class
      );
      return new LiteratureProxyResponse(
        response.getStatusCode(),
        response.getBody() == null ? objectMapper.createObjectNode() : response.getBody()
      );
    } catch (HttpStatusCodeException ex) {
      return new LiteratureProxyResponse(ex.getStatusCode(), parseErrorBody(ex));
    } catch (ResourceAccessException ex) {
      return error(HttpStatus.SERVICE_UNAVAILABLE, "PDF_PARSER_UNAVAILABLE", "The PDF parsing service is not available right now.");
    } catch (RuntimeException ex) {
      return error(HttpStatus.BAD_GATEWAY, "PDF_PARSER_INVALID_RESPONSE", "The PDF parsing service returned an invalid response.");
    }
  }

  public LiteratureProxyResponse publicGet(String path, String rawQuery) {
    String safePath = normalizePath(path);
    boolean paperPath = safePath.matches("/paper/[1-9][0-9]*(?:/(?:similar|knowledge|methods|data_points|citations|authors))?");
    boolean authorPath = safePath.matches("/author/[1-9][0-9]*(?:/(?:papers|network))?");
    if (!PUBLIC_PATHS.contains(safePath) && !paperPath && !authorPath) {
      return error(HttpStatus.NOT_FOUND, "LITERATURE_ROUTE_NOT_FOUND", "This literature function is not available on the public API.");
    }
    if ("/stats".equals(safePath)) {
      if (internalToken.isBlank()) {
        return error(HttpStatus.SERVICE_UNAVAILABLE, "LITERATURE_STATS_NOT_CONFIGURED", "Literature statistics are not configured.");
      }
      HttpHeaders headers = new HttpHeaders();
      headers.set("X-OpenIsle-Internal-Token", internalToken);
      return exchange(withQuery(baseUrl + safePath, rawQuery), HttpMethod.GET, new HttpEntity<>(headers));
    }
    return getAbsolute(withQuery(baseUrl + safePath, rawQuery));
  }

  public LiteratureProxyResponse admin(String method, String path, String rawQuery, JsonNode body) {
    String safePath = normalizePath(path);
    boolean progressPath = safePath.matches("/progress/[A-Za-z0-9_-]+");
    if (!ADMIN_PATHS.contains(safePath) && !progressPath) {
      return error(HttpStatus.NOT_FOUND, "LITERATURE_ADMIN_ROUTE_NOT_FOUND", "Unknown literature administration operation.");
    }
    if (internalToken.isBlank()) {
      return error(HttpStatus.SERVICE_UNAVAILABLE, "LITERATURE_ADMIN_NOT_CONFIGURED", "The literature administration bridge is not configured.");
    }
    HttpMethod httpMethod = "POST".equalsIgnoreCase(method) ? HttpMethod.POST : HttpMethod.GET;
    HttpHeaders headers = new HttpHeaders();
    headers.set("X-OpenIsle-Internal-Token", internalToken);
    headers.setContentType(MediaType.APPLICATION_JSON);
    return exchange(withQuery(baseUrl + safePath, rawQuery), httpMethod, new HttpEntity<>(body, headers));
  }

  private String normalizePath(String path) {
    String result = "/" + (path == null ? "" : path).replace('\\', '/').replaceAll("^/+|/+$", "");
    if (result.contains("..") || !result.matches("/[A-Za-z0-9_/-]*")) throw new IllegalArgumentException("Invalid literature path");
    return result;
  }

  private String withQuery(String url, String rawQuery) {
    if (rawQuery == null || rawQuery.isBlank()) return url;
    if (rawQuery.length() > 4000 || rawQuery.contains("#") || rawQuery.contains("\\r") || rawQuery.contains("\\n")) {
      throw new IllegalArgumentException("Invalid literature query");
    }
    return url + "?" + rawQuery;
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
    return exchange(url, HttpMethod.GET, HttpEntity.EMPTY);
  }

  private LiteratureProxyResponse exchange(String url, HttpMethod method, HttpEntity<?> entity) {
    try {
      ResponseEntity<JsonNode> response = restTemplate.exchange(URI.create(url), method, entity, JsonNode.class);
      JsonNode body = response.getBody() == null ? objectMapper.createObjectNode() : response.getBody();
      return new LiteratureProxyResponse(response.getStatusCode(), body);
    } catch (HttpStatusCodeException ex) {
      HttpStatusCode status = ex.getStatusCode();
      if (status.is4xxClientError()) return new LiteratureProxyResponse(status, parseErrorBody(ex));
      return error(HttpStatus.BAD_GATEWAY, "LITERATURE_UPSTREAM_ERROR", "The literature service returned an unexpected response.");
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
  public record LiteratureFileResponse(HttpStatusCode status, byte[] body, MediaType contentType) {}
}
