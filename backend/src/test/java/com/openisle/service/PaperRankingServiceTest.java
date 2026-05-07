package com.openisle.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.openisle.dto.AuthorRankingDto;
import com.openisle.dto.InstitutionRankingDto;
import com.openisle.dto.PaperRankingDto;
import com.openisle.model.Institution;
import com.openisle.model.PaperAuthor;
import com.openisle.model.PaperProfile;
import com.openisle.model.PaperPublicationStatus;
import com.openisle.model.PaperScoreSnapshot;
import com.openisle.model.Post;
import com.openisle.repository.PaperAuthorRepository;
import com.openisle.repository.PaperScoreSnapshotRepository;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.PageRequest;

class PaperRankingServiceTest {

  @Test
  void listTopPapersReturnsPublishedScoreSnapshotsInScoreOrder() {
    PaperScoreSnapshotRepository snapshotRepository = mock(PaperScoreSnapshotRepository.class);
    PaperAuthorRepository authorRepository = mock(PaperAuthorRepository.class);
    PaperRankingService service = new PaperRankingService(
      snapshotRepository,
      authorRepository,
      new PaperAccessPolicy(authorRepository)
    );

    PaperScoreSnapshot top = snapshot(1L, "Top Paper", 4.8, 12);
    PaperScoreSnapshot second = snapshot(2L, "Second Paper", 4.4, 8);

    when(
      snapshotRepository.findByRatingCountGreaterThanAndPaperPublicationStatusOrderByCompositeScoreDesc(
        0,
        PaperPublicationStatus.PUBLISHED,
        PageRequest.of(0, 10)
      )
    ).thenReturn(List.of(top, second));

    List<PaperRankingDto> result = service.listTopPapers(10);

    assertEquals(2, result.size());
    assertEquals(1, result.get(0).getRank());
    assertEquals("Top Paper", result.get(0).getTitle());
    assertEquals(4.8, result.get(0).getCompositeScore());
    assertEquals(12, result.get(0).getRatingCount());
  }

  @Test
  void listAuthorRankingsAggregatesScoresAcrossAuthorPapers() {
    PaperScoreSnapshotRepository snapshotRepository = mock(PaperScoreSnapshotRepository.class);
    PaperAuthorRepository authorRepository = mock(PaperAuthorRepository.class);
    PaperRankingService service = new PaperRankingService(
      snapshotRepository,
      authorRepository,
      new PaperAccessPolicy(authorRepository)
    );

    PaperScoreSnapshot first = snapshot(1L, "Paper A", 5.0, 5);
    PaperScoreSnapshot second = snapshot(2L, "Paper B", 4.0, 3);
    PaperScoreSnapshot third = snapshot(3L, "Paper C", 3.0, 2);

    when(
      snapshotRepository.findByRatingCountGreaterThanAndPaperPublicationStatus(
        0,
        PaperPublicationStatus.PUBLISHED
      )
    ).thenReturn(List.of(first, second, third));
    when(authorRepository.findByPaperIdOrderByAuthorOrderAsc(1L)).thenReturn(List.of(author("Alice", null)));
    when(authorRepository.findByPaperIdOrderByAuthorOrderAsc(2L)).thenReturn(List.of(author("Alice", null)));
    when(authorRepository.findByPaperIdOrderByAuthorOrderAsc(3L)).thenReturn(List.of(author("Bob", null)));

    List<AuthorRankingDto> result = service.listAuthorRankings(10);

    assertEquals(2, result.size());
    assertEquals("Alice", result.get(0).getAuthorName());
    assertEquals(2, result.get(0).getPaperCount());
    assertEquals(4.5, result.get(0).getAverageCompositeScore());
    assertEquals("Bob", result.get(1).getAuthorName());
  }

  @Test
  void listInstitutionRankingsAggregatesScoresAcrossInstitutions() {
    PaperScoreSnapshotRepository snapshotRepository = mock(PaperScoreSnapshotRepository.class);
    PaperAuthorRepository authorRepository = mock(PaperAuthorRepository.class);
    PaperRankingService service = new PaperRankingService(
      snapshotRepository,
      authorRepository,
      new PaperAccessPolicy(authorRepository)
    );

    PaperScoreSnapshot first = snapshot(1L, "Paper A", 5.0, 5);
    PaperScoreSnapshot second = snapshot(2L, "Paper B", 4.0, 3);

    when(
      snapshotRepository.findByRatingCountGreaterThanAndPaperPublicationStatus(
        0,
        PaperPublicationStatus.PUBLISHED
      )
    ).thenReturn(List.of(first, second));
    when(authorRepository.findByPaperIdOrderByAuthorOrderAsc(1L)).thenReturn(
      List.of(author("Alice", "Example University"))
    );
    when(authorRepository.findByPaperIdOrderByAuthorOrderAsc(2L)).thenReturn(
      List.of(author("Bob", "Example University"))
    );

    List<InstitutionRankingDto> result = service.listInstitutionRankings(10);

    assertEquals(1, result.size());
    assertEquals("Example University", result.get(0).getInstitutionName());
    assertEquals(2, result.get(0).getPaperCount());
    assertEquals(4.5, result.get(0).getAverageCompositeScore());
  }

  private PaperScoreSnapshot snapshot(Long paperId, String title, double compositeScore, int ratingCount) {
    Post post = new Post();
    post.setId(paperId + 100);

    PaperProfile paper = new PaperProfile();
    paper.setId(paperId);
    paper.setPost(post);
    paper.setTitle(title);
    paper.setSubjectArea("Information Systems");
    paper.setPublicationStatus(PaperPublicationStatus.PUBLISHED);

    PaperScoreSnapshot snapshot = new PaperScoreSnapshot();
    snapshot.setPaper(paper);
    snapshot.setCompositeScore(compositeScore);
    snapshot.setRatingCount(ratingCount);
    snapshot.setAverageOverallScore(compositeScore);
    return snapshot;
  }

  private PaperAuthor author(String name, String institutionName) {
    PaperAuthor author = new PaperAuthor();
    author.setDisplayName(name);
    if (institutionName != null) {
      Institution institution = new Institution();
      institution.setName(institutionName);
      author.setInstitution(institution);
    }
    return author;
  }
}
