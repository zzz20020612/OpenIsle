package com.openisle.controller;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.openisle.config.CustomAccessDeniedHandler;
import com.openisle.config.SecurityConfig;
import com.openisle.repository.UserRepository;
import com.openisle.service.JwtService;
import com.openisle.service.LiteratureIntegrationService;
import com.openisle.service.LiteratureAdminAuditService;
import com.openisle.service.LiteratureIntegrationService.LiteratureProxyResponse;
import com.openisle.service.LiteratureRatingService;
import com.openisle.service.UserVisitService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(LiteratureController.class)
@AutoConfigureMockMvc
@Import({ SecurityConfig.class, CustomAccessDeniedHandler.class })
class LiteratureControllerTest {

  @Autowired
  private MockMvc mockMvc;

  @MockBean
  private LiteratureIntegrationService literatureService;

  @MockBean
  private LiteratureRatingService literatureRatingService;

  @MockBean
  private LiteratureAdminAuditService literatureAdminAuditService;

  @MockBean
  private JwtService jwtService;

  @MockBean
  private UserRepository userRepository;

  @MockBean
  private UserVisitService userVisitService;

  @MockBean
  private RedisTemplate<?, ?> redisTemplate;

  @Test
  void healthIsPublicWithoutJwt() throws Exception {
    var body = JsonNodeFactory.instance.objectNode();
    body.put("status", "ok");
    when(literatureService.health()).thenReturn(new LiteratureProxyResponse(HttpStatus.OK, body));

    mockMvc
      .perform(get("/api/literature/health"))
      .andExpect(status().isOk())
      .andExpect(jsonPath("$.status").value("ok"));
  }
}
