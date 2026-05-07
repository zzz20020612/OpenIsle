package com.openisle.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openisle.dto.PaperRatingRequest;
import com.openisle.dto.PaperRatingResponse;
import com.openisle.model.PaperProfile;
import com.openisle.model.PaperPublicationStatus;
import com.openisle.model.PaperRating;
import com.openisle.model.PaperScoreSnapshot;
import com.openisle.model.Post;
import com.openisle.model.User;
import com.openisle.repository.PaperProfileRepository;
import com.openisle.repository.PaperRatingRepository;
import com.openisle.repository.PaperScoreSnapshotRepository;
import com.openisle.repository.UserRepository;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;

class PaperRatingServiceTest {

  @Test
  void ratePaperCreatesRatingAndUpdatesScoreSnapshot() {
    PaperProfileRepository paperProfileRepository = mock(PaperProfileRepository.class);
    PaperRatingRepository paperRatingRepository = mock(PaperRatingRepository.class);
    PaperScoreSnapshotRepository paperScoreSnapshotRepository = mock(
      PaperScoreSnapshotRepository.class
    );
    UserRepository userRepository = mock(UserRepository.class);

    PaperRatingService service = new PaperRatingService(
      paperProfileRepository,
      paperRatingRepository,
      paperScoreSnapshotRepository,
      userRepository,
      new PaperAccessPolicy(mock(com.openisle.repository.PaperAuthorRepository.class))
    );

    User rater = new User();
    rater.setId(9L);
    rater.setUsername("reader");

    Post post = new Post();
    post.setId(22L);

    PaperProfile paper = new PaperProfile();
    paper.setId(7L);
    paper.setPost(post);
    paper.setTitle("A Rated Paper");
    paper.setPublicationStatus(PaperPublicationStatus.PUBLISHED);

    AtomicReference<PaperRating> savedRating = new AtomicReference<>();

    when(userRepository.findByUsername("reader")).thenReturn(Optional.of(rater));
    when(paperProfileRepository.findById(7L)).thenReturn(Optional.of(paper));
    when(paperRatingRepository.findByPaperIdAndRaterId(7L, 9L)).thenReturn(Optional.empty());
    when(paperRatingRepository.save(any(PaperRating.class))).thenAnswer(invocation -> {
      PaperRating rating = invocation.getArgument(0);
      rating.setId(100L);
      savedRating.set(rating);
      return rating;
    });
    when(paperRatingRepository.findByPaperId(7L)).thenAnswer(invocation ->
      List.of(savedRating.get())
    );
    when(paperScoreSnapshotRepository.findByPaperId(7L)).thenReturn(Optional.empty());
    when(paperScoreSnapshotRepository.save(any(PaperScoreSnapshot.class))).thenAnswer(invocation -> {
      PaperScoreSnapshot snapshot = invocation.getArgument(0);
      snapshot.setId(200L);
      return snapshot;
    });

    PaperRatingRequest request = new PaperRatingRequest();
    request.setOverallScore(5);
    request.setInnovationScore(4);
    request.setMethodScore(5);
    request.setImpactScore(4);
    request.setComment("Strong and useful paper.");

    PaperRatingResponse response = service.ratePaper("reader", 7L, request);

    assertNotNull(response.getRatingId());
    assertEquals(7L, response.getPaperId());
    assertEquals(5, response.getOverallScore());
    assertEquals("Strong and useful paper.", response.getComment());
    assertEquals(1, response.getScoreSnapshot().getRatingCount());
    assertEquals(5.0, response.getScoreSnapshot().getAverageOverallScore());
    assertEquals(4.5, response.getScoreSnapshot().getCompositeScore());
  }

  @Test
  void ratePaperRejectsPaperCreatorSelfRating() {
    PaperProfileRepository paperProfileRepository = mock(PaperProfileRepository.class);
    PaperRatingRepository paperRatingRepository = mock(PaperRatingRepository.class);
    PaperScoreSnapshotRepository paperScoreSnapshotRepository = mock(
      PaperScoreSnapshotRepository.class
    );
    UserRepository userRepository = mock(UserRepository.class);

    PaperRatingService service = new PaperRatingService(
      paperProfileRepository,
      paperRatingRepository,
      paperScoreSnapshotRepository,
      userRepository,
      new PaperAccessPolicy(mock(com.openisle.repository.PaperAuthorRepository.class))
    );

    User author = new User();
    author.setId(9L);
    author.setUsername("author");

    PaperProfile paper = new PaperProfile();
    paper.setId(7L);
    paper.setCreatedBy(author);
    paper.setPublicationStatus(PaperPublicationStatus.PUBLISHED);

    when(userRepository.findByUsername("author")).thenReturn(Optional.of(author));
    when(paperProfileRepository.findById(7L)).thenReturn(Optional.of(paper));

    PaperRatingRequest request = new PaperRatingRequest();
    request.setOverallScore(5);
    request.setInnovationScore(4);
    request.setMethodScore(5);
    request.setImpactScore(4);

    IllegalArgumentException exception = assertThrows(
      IllegalArgumentException.class,
      () -> service.ratePaper("author", 7L, request)
    );

    assertEquals("Authors cannot rate their own papers", exception.getMessage());
    verify(paperRatingRepository, never()).save(any(PaperRating.class));
  }

  @Test
  void ratePaperRejectsUnpublishedPaper() {
    PaperProfileRepository paperProfileRepository = mock(PaperProfileRepository.class);
    PaperRatingRepository paperRatingRepository = mock(PaperRatingRepository.class);
    PaperScoreSnapshotRepository paperScoreSnapshotRepository = mock(
      PaperScoreSnapshotRepository.class
    );
    UserRepository userRepository = mock(UserRepository.class);

    PaperRatingService service = new PaperRatingService(
      paperProfileRepository,
      paperRatingRepository,
      paperScoreSnapshotRepository,
      userRepository,
      new PaperAccessPolicy(mock(com.openisle.repository.PaperAuthorRepository.class))
    );

    User reader = new User();
    reader.setId(9L);
    reader.setUsername("reader");

    PaperProfile paper = new PaperProfile();
    paper.setId(7L);
    paper.setPublicationStatus(PaperPublicationStatus.SCREENING);

    when(userRepository.findByUsername("reader")).thenReturn(Optional.of(reader));
    when(paperProfileRepository.findById(7L)).thenReturn(Optional.of(paper));

    PaperRatingRequest request = new PaperRatingRequest();
    request.setOverallScore(5);
    request.setInnovationScore(4);
    request.setMethodScore(5);
    request.setImpactScore(4);

    IllegalArgumentException exception = assertThrows(
      IllegalArgumentException.class,
      () -> service.ratePaper("reader", 7L, request)
    );

    assertEquals("This paper is not eligible for rating", exception.getMessage());
    verify(paperRatingRepository, never()).save(any(PaperRating.class));
  }
}
