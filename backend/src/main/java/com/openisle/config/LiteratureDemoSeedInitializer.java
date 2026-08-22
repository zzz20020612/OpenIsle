package com.openisle.config;

import com.fasterxml.jackson.databind.JsonNode;
import com.openisle.service.LiteratureDemoSeedService;
import com.openisle.service.LiteratureIntegrationService;
import java.util.ArrayList;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/** Explicitly gated initializer for local ranking demonstrations. */
@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnProperty(name = "literature.demo-seed.enabled", havingValue = "true")
public class LiteratureDemoSeedInitializer implements CommandLineRunner {

  private final LiteratureIntegrationService integrationService;
  private final LiteratureDemoSeedService seedService;

  @Override
  public void run(String... args) {
    JsonNode body = integrationService.listPapers(null, "year_desc", 1000, 0).body();
    List<Long> completePaperIds = new ArrayList<>();
    for (JsonNode paper : body.path("papers")) {
      if (paper.path("completeness").path("complete").asBoolean(false)) {
        completePaperIds.add(paper.path("id").asLong());
      }
      if (completePaperIds.size() == 5) break;
    }
    if (completePaperIds.size() < 5) {
      log.warn("Literature demo ratings not seeded: only {} complete papers are available", completePaperIds.size());
      return;
    }
    LiteratureDemoSeedService.SeedResult result = seedService.seed(completePaperIds);
    log.info(
      "Literature demo ratings ready: users={}, papers={}, ratings={}",
      result.usersAvailable(), result.papersRated(), result.ratingsWritten()
    );
  }
}
