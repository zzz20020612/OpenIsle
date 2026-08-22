package com.openisle.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.openisle.dto.LiteratureRatingRequest;
import com.openisle.dto.LiteratureRatingResponse;
import com.openisle.model.LiteratureRating;
import com.openisle.model.LiteratureScoreSnapshot;
import com.openisle.model.User;
import com.openisle.repository.LiteratureRatingRepository;
import com.openisle.repository.LiteratureScoreSnapshotRepository;
import com.openisle.repository.UserRepository;
import com.openisle.service.LiteratureIntegrationService.LiteratureProxyResponse;
import java.util.List;
import java.util.ArrayList;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

class LiteratureRatingServiceTest {

  @Test
  void registeredUserCreatesSixDimensionalRatingAndSnapshot() {
    LiteratureRatingRepository ratingRepository = mock(LiteratureRatingRepository.class);
    LiteratureScoreSnapshotRepository snapshotRepository = mock(LiteratureScoreSnapshotRepository.class);
    UserRepository userRepository = mock(UserRepository.class);
    LiteratureIntegrationService integrationService = mock(LiteratureIntegrationService.class);
    LiteratureRatingService service = new LiteratureRatingService(
      ratingRepository,
      snapshotRepository,
      userRepository,
      integrationService,
      mock(LiteratureReviewTaskService.class)
    );

    User reader = new User();
    reader.setId(9L);
    reader.setUsername("user1");
    reader.setEmail("user1@example.edu");
    AtomicReference<LiteratureRating> saved = new AtomicReference<>();

    when(integrationService.getPaper(7L)).thenReturn(
      new LiteratureProxyResponse(HttpStatus.OK, JsonNodeFactory.instance.objectNode())
    );
    when(userRepository.findByUsername("user1")).thenReturn(Optional.of(reader));
    when(ratingRepository.findByLiteraturePaperIdAndRaterId(7L, 9L)).thenReturn(Optional.empty());
    when(ratingRepository.save(any(LiteratureRating.class))).thenAnswer(invocation -> {
      LiteratureRating rating = invocation.getArgument(0);
      rating.setId(100L);
      saved.set(rating);
      return rating;
    });
    when(ratingRepository.findByLiteraturePaperId(7L)).thenAnswer(invocation -> List.of(saved.get()));
    when(snapshotRepository.findByLiteraturePaperId(7L)).thenReturn(Optional.empty());
    when(snapshotRepository.save(any(LiteratureScoreSnapshot.class))).thenAnswer(invocation -> invocation.getArgument(0));

    LiteratureRatingResponse response = service.rateLiterature("user1", 7L, validRequest());

    assertNotNull(response.getRatingId());
    assertEquals(7L, response.getLiteraturePaperId());
    assertEquals("user1", response.getRaterUsername());
    assertEquals(1, response.getScoreSnapshot().getRatingCount());
    assertEquals("INITIAL", response.getScoreSnapshot().getRankingStatus());
    assertEquals(4.0, response.getScoreSnapshot().getUnshrunkCompositeScore());
    assertEquals(null, response.getScoreSnapshot().getCompositeScore());
  }

  @Test
  void rejectsRatingWithoutReadingConfirmation() {
    LiteratureRatingRepository ratingRepository = mock(LiteratureRatingRepository.class);
    LiteratureRatingService service = new LiteratureRatingService(
      ratingRepository,
      mock(LiteratureScoreSnapshotRepository.class),
      mock(UserRepository.class),
      mock(LiteratureIntegrationService.class),
      mock(LiteratureReviewTaskService.class)
    );
    LiteratureRatingRequest request = validRequest();
    request.setReadConfirmed(false);

    assertThrows(IllegalArgumentException.class, () -> service.rateLiterature("user1", 7L, request));
    verify(ratingRepository, never()).save(any());
  }

  @Test
  void acceptsExplicitZeroScore() {
    LiteratureRatingRepository ratingRepository = mock(LiteratureRatingRepository.class);
    LiteratureScoreSnapshotRepository snapshotRepository = mock(LiteratureScoreSnapshotRepository.class);
    UserRepository userRepository = mock(UserRepository.class);
    LiteratureIntegrationService integrationService = mock(LiteratureIntegrationService.class);
    LiteratureRatingService service = new LiteratureRatingService(
      ratingRepository, snapshotRepository, userRepository, integrationService, mock(LiteratureReviewTaskService.class)
    );
    User reader = new User();
    reader.setId(3L);
    reader.setUsername("reader");
    reader.setEmail("reader@lab.edu");
    AtomicReference<LiteratureRating> saved = new AtomicReference<>();
    when(integrationService.getPaper(7L)).thenReturn(new LiteratureProxyResponse(HttpStatus.OK, JsonNodeFactory.instance.objectNode()));
    when(userRepository.findByUsername("reader")).thenReturn(Optional.of(reader));
    when(ratingRepository.findByLiteraturePaperIdAndRaterId(7L, 3L)).thenReturn(Optional.empty());
    when(ratingRepository.save(any(LiteratureRating.class))).thenAnswer(invocation -> { saved.set(invocation.getArgument(0)); return saved.get(); });
    when(ratingRepository.findByLiteraturePaperId(7L)).thenAnswer(invocation -> List.of(saved.get()));
    when(snapshotRepository.findByLiteraturePaperId(7L)).thenReturn(Optional.empty());
    when(snapshotRepository.save(any(LiteratureScoreSnapshot.class))).thenAnswer(invocation -> invocation.getArgument(0));
    LiteratureRatingRequest request = validRequest();
    request.setOriginalityScore(0);

    LiteratureRatingResponse response = service.rateLiterature("reader", 7L, request);

    assertEquals(0, response.getOriginalityScore());
    assertEquals(3.0, response.getScoreSnapshot().getUnshrunkCompositeScore());
  }

  @Test
  void tenInstitutionDiverseRatingsCreateFormalRankingEntry() {
    LiteratureRatingRepository ratingRepository = mock(LiteratureRatingRepository.class);
    LiteratureScoreSnapshotRepository snapshotRepository = mock(LiteratureScoreSnapshotRepository.class);
    UserRepository userRepository = mock(UserRepository.class);
    LiteratureIntegrationService integrationService = mock(LiteratureIntegrationService.class);
    LiteratureRatingService service = new LiteratureRatingService(
      ratingRepository, snapshotRepository, userRepository, integrationService, mock(LiteratureReviewTaskService.class)
    );
    List<LiteratureRating> ratings = new ArrayList<>();
    AtomicReference<LiteratureScoreSnapshot> snapshot = new AtomicReference<>();
    when(integrationService.getPaper(7L)).thenReturn(new LiteratureProxyResponse(HttpStatus.OK, JsonNodeFactory.instance.objectNode()));
    when(userRepository.findByUsername(any())).thenAnswer(invocation -> {
      String username = invocation.getArgument(0);
      int index = Integer.parseInt(username.substring(1));
      User user = new User();
      user.setId((long) index + 1);
      user.setUsername(username);
      String domain = index < 4 ? "alpha.edu" : index < 7 ? "beta.edu" : "gamma.edu";
      user.setEmail(username + "@" + domain);
      return Optional.of(user);
    });
    when(ratingRepository.findByLiteraturePaperIdAndRaterId(any(), any())).thenReturn(Optional.empty());
    when(ratingRepository.save(any(LiteratureRating.class))).thenAnswer(invocation -> {
      LiteratureRating rating = invocation.getArgument(0);
      rating.setId((long) ratings.size() + 1);
      ratings.add(rating);
      return rating;
    });
    when(ratingRepository.findByLiteraturePaperId(7L)).thenAnswer(invocation -> List.copyOf(ratings));
    when(snapshotRepository.findByLiteraturePaperId(7L)).thenAnswer(invocation -> Optional.ofNullable(snapshot.get()));
    when(snapshotRepository.save(any(LiteratureScoreSnapshot.class))).thenAnswer(invocation -> {
      snapshot.set(invocation.getArgument(0));
      return snapshot.get();
    });

    LiteratureRatingResponse finalResponse = null;
    for (int index = 0; index < 10; index++) {
      finalResponse = service.rateLiterature("u" + index, 7L, validRequest());
    }

    assertNotNull(finalResponse);
    assertEquals("FORMAL", finalResponse.getScoreSnapshot().getRankingStatus());
    assertTrue(finalResponse.getScoreSnapshot().isRankingEligible());
    assertEquals(10.0, finalResponse.getScoreSnapshot().getEffectiveSampleSize());
    assertEquals(3, finalResponse.getScoreSnapshot().getInstitutionCount());
    assertEquals(0.4, finalResponse.getScoreSnapshot().getLargestInstitutionShare());
    assertEquals(3.75, finalResponse.getScoreSnapshot().getCompositeScore());

    var metadata = JsonNodeFactory.instance.objectNode();
    var paper = metadata.putArray("papers").addObject();
    paper.put("id", 7);
    paper.put("title", "A formally evaluated paper");
    paper.putArray("author").add("A. Scholar");
    when(snapshotRepository.findAll()).thenReturn(List.of(snapshot.get()));
    when(integrationService.listPapers(null, "year_desc", 100, 0)).thenReturn(
      new LiteratureProxyResponse(HttpStatus.OK, metadata)
    );

    assertEquals(1, service.rankPapers(10).size());
  }

  private LiteratureRatingRequest validRequest() {
    LiteratureRatingRequest request = new LiteratureRatingRequest();
    request.setOriginalityScore(4);
    request.setRigorScore(4);
    request.setEvidenceScore(4);
    request.setSignificanceScore(4);
    request.setReproducibilityScore(4);
    request.setClarityScore(4);
    request.setReadConfirmed(true);
    request.setComment("Clear strengths and limitations supported by the paper.");
    return request;
  }
}
