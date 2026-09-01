package com.openisle.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

class LiteratureIntegrationServiceTest {

  private final ObjectMapper objectMapper = new ObjectMapper();

  @Test
  void listPapersEncodesSearchAndConstrainsPagingAndSort() {
    RestTemplate restTemplate = new RestTemplate();
    MockRestServiceServer server = MockRestServiceServer.createServer(restTemplate);
    LiteratureIntegrationService service = new LiteratureIntegrationService(
      "http://literature.test/",
      restTemplate,
      objectMapper
    );

    server
      .expect(requestTo("http://literature.test/papers/list?sort=year_desc&limit=100&offset=0&q=deep%20learning"))
      .andRespond(withSuccess("{\"total\":1,\"papers\":[{\"id\":7}]}", MediaType.APPLICATION_JSON));

    var response = service.listPapers(" deep learning ", "unsafe_sort", 500, -10);

    assertThat(response.status()).isEqualTo(HttpStatus.OK);
    assertThat(response.body().path("papers").get(0).path("id").asInt()).isEqualTo(7);
    server.verify();
  }

  @Test
  void unavailableServiceReturnsStableServiceUnavailableResponse() {
    RestTemplate restTemplate = new RestTemplate();
    MockRestServiceServer server = MockRestServiceServer.createServer(restTemplate);
    LiteratureIntegrationService service = new LiteratureIntegrationService(
      "http://literature.test",
      restTemplate,
      objectMapper
    );

    server.expect(requestTo("http://literature.test/health")).andRespond(request -> {
      throw new java.net.ConnectException("connection refused");
    });

    var response = service.health();

    assertThat(response.status()).isEqualTo(HttpStatus.SERVICE_UNAVAILABLE);
    assertThat(response.body().path("code").asText()).isEqualTo("LITERATURE_SERVICE_UNAVAILABLE");
  }

  @Test
  void publicStatsUsesTheInternalEngineCredential() {
    RestTemplate restTemplate = new RestTemplate();
    MockRestServiceServer server = MockRestServiceServer.createServer(restTemplate);
    LiteratureIntegrationService service = new LiteratureIntegrationService(
      "http://literature.test",
      restTemplate,
      objectMapper,
      "internal-test-token"
    );

    server.expect(requestTo("http://literature.test/stats"))
      .andExpect(header("X-OpenIsle-Internal-Token", "internal-test-token"))
      .andRespond(withSuccess("{\"total_papers\":75}", MediaType.APPLICATION_JSON));

    var response = service.publicGet("/stats", null);

    assertThat(response.status()).isEqualTo(HttpStatus.OK);
    assertThat(response.body().path("total_papers").asInt()).isEqualTo(75);
    server.verify();
  }

  @Test
  void graphDiagnosticsRemainAvailableToThePublicNetworkPage() {
    RestTemplate restTemplate = new RestTemplate();
    MockRestServiceServer server = MockRestServiceServer.createServer(restTemplate);
    LiteratureIntegrationService service = new LiteratureIntegrationService(
      "http://literature.test",
      restTemplate,
      objectMapper,
      "internal-test-token"
    );

    server.expect(requestTo("http://literature.test/graph/diagnostics?max_nodes=80"))
      .andRespond(withSuccess("{\"issue_count\":0,\"issues\":[]}", MediaType.APPLICATION_JSON));

    var response = service.publicGet("/graph/diagnostics", "max_nodes=80");

    assertThat(response.status()).isEqualTo(HttpStatus.OK);
    assertThat(response.body().path("issue_count").asInt()).isZero();
    server.verify();
  }
}
