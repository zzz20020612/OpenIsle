package com.openisle.service;

import com.openisle.dto.AiScreeningServiceRequest;
import com.openisle.dto.AiScreeningServiceResponse;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

@Service
public class AiScreeningClient {

  private final String serviceUrl;
  private final String serviceToken;
  private final RestTemplate restTemplate;

  public AiScreeningClient(
    @Value("${ai-screening.service-url:http://ai-screening:8090}") String serviceUrl,
    @Value("${ai-screening.service-token:}") String serviceToken,
    @Value("${ai-screening.timeout-seconds:180}") int timeoutSeconds
  ) {
    this(serviceUrl, serviceToken, restTemplate(timeoutSeconds));
  }

  AiScreeningClient(String serviceUrl, String serviceToken, RestTemplate restTemplate) {
    this.serviceUrl = serviceUrl.replaceAll("/+$", "");
    this.serviceToken = serviceToken;
    this.restTemplate = restTemplate;
  }

  public AiScreeningServiceResponse screen(AiScreeningServiceRequest request) {
    if (serviceToken == null || serviceToken.isBlank()) {
      throw new IllegalStateException("AI_SCREENING_SERVICE_TOKEN is required");
    }
    HttpHeaders headers = new HttpHeaders();
    headers.setContentType(MediaType.APPLICATION_JSON);
    headers.setBearerAuth(serviceToken);
    return restTemplate.postForObject(
      serviceUrl + "/v1/screenings",
      new HttpEntity<>(request, headers),
      AiScreeningServiceResponse.class
    );
  }

  private static RestTemplate restTemplate(int timeoutSeconds) {
    int timeoutMillis = Math.toIntExact(Duration.ofSeconds(timeoutSeconds).toMillis());
    SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
    factory.setConnectTimeout(Math.min(timeoutMillis, 30_000));
    factory.setReadTimeout(timeoutMillis);
    return new RestTemplate(factory);
  }
}
