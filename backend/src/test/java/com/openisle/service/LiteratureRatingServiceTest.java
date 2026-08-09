package com.openisle.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
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
      integrationService
    );

    User reader = new User();
    reader.setId(9L);
    reader.setUsername("user1");
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
    assertEquals(4.0, response.getScoreSnapshot().getCompositeScore());
  }

  @Test
  void rejectsRatingWithoutReadingConfirmation() {
    LiteratureRatingRepository ratingRepository = mock(LiteratureRatingRepository.class);
    LiteratureRatingService service = new LiteratureRatingService(
      ratingRepository,
      mock(LiteratureScoreSnapshotRepository.class),
      mock(UserRepository.class),
      mock(LiteratureIntegrationService.class)
    );
    LiteratureRatingRequest request = validRequest();
    request.setReadConfirmed(false);

    assertThrows(IllegalArgumentException.class, () -> service.rateLiterature("user1", 7L, request));
    verify(ratingRepository, never()).save(any());
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
