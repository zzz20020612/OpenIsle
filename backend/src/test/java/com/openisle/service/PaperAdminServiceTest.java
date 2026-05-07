package com.openisle.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.openisle.model.PaperProfile;
import com.openisle.model.PaperPublicationStatus;
import com.openisle.model.PaperScreeningStatus;
import com.openisle.model.Post;
import com.openisle.model.PostStatus;
import com.openisle.model.User;
import com.openisle.repository.AiScreeningResultRepository;
import com.openisle.repository.PaperAuthorRepository;
import com.openisle.repository.PaperProfileRepository;
import com.openisle.repository.PaperScoreSnapshotRepository;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;

class PaperAdminServiceTest {

  @Test
  void listPapersIncludesNonPublishedStatusesAndLinkedPostSignals() {
    PaperProfileRepository paperProfileRepository = mock(PaperProfileRepository.class);
    PaperAuthorRepository paperAuthorRepository = mock(PaperAuthorRepository.class);
    PaperScoreSnapshotRepository paperScoreSnapshotRepository = mock(
      PaperScoreSnapshotRepository.class
    );
    PaperAdminService service = new PaperAdminService(
      paperProfileRepository,
      paperAuthorRepository,
      mock(AiScreeningResultRepository.class),
      paperScoreSnapshotRepository,
      mock(PostService.class)
    );

    PaperProfile screeningPaper = buildPaper(
      1L,
      "Screening Paper",
      PaperPublicationStatus.SCREENING,
      PostStatus.PENDING
    );
    PaperProfile publishedPaper = buildPaper(
      2L,
      "Published Paper",
      PaperPublicationStatus.PUBLISHED,
      PostStatus.PUBLISHED
    );
    publishedPaper.getPost().setClosed(true);

    when(paperProfileRepository.findAll(any(Pageable.class))).thenReturn(
      new PageImpl<>(List.of(screeningPaper, publishedPaper))
    );
    when(paperAuthorRepository.findByPaperIdOrderByAuthorOrderAsc(any())).thenReturn(List.of());

    var result = service.listPapers(0, 20, null);

    assertEquals(2, result.size());
    assertEquals(PaperPublicationStatus.SCREENING, result.get(0).getPublicationStatus());
    assertEquals(PostStatus.PENDING, result.get(0).getPostStatus());
    assertEquals(false, result.get(0).isDiscussionClosed());
    assertEquals(true, result.get(1).isDiscussionClosed());
  }

  @Test
  void listPapersExposesLinkedPostDistributionStateWithoutOwningPostActions() {
    PaperProfileRepository paperProfileRepository = mock(PaperProfileRepository.class);
    PaperAdminService service = new PaperAdminService(
      paperProfileRepository,
      mock(PaperAuthorRepository.class),
      mock(AiScreeningResultRepository.class),
      mock(PaperScoreSnapshotRepository.class),
      mock(PostService.class)
    );

    PaperProfile paper = buildPaper(
      10L,
      "Featured Paper",
      PaperPublicationStatus.PUBLISHED,
      PostStatus.PUBLISHED
    );
    paper.setScreeningStatus(PaperScreeningStatus.PASSED);
    paper.getPost().setPinnedAt(java.time.LocalDateTime.now());
    paper.getPost().setRssExcluded(false);

    when(paperProfileRepository.findAll(any(Pageable.class))).thenReturn(new PageImpl<>(List.of(paper)));

    var result = service.listPapers(0, 20, null);

    assertEquals(1, result.size());
    assertEquals(PaperPublicationStatus.PUBLISHED, result.get(0).getPublicationStatus());
    assertEquals(PaperScreeningStatus.PASSED, result.get(0).getScreeningStatus());
    assertEquals(true, result.get(0).isPinned());
    assertEquals(false, result.get(0).isRssExcluded());
  }

  @Test
  void retractPaperKeepsTheOperationInAdminModerationAndHidesLinkedPost() {
    PaperProfileRepository paperProfileRepository = mock(PaperProfileRepository.class);
    PostService postService = mock(PostService.class);
    PaperAdminService service = new PaperAdminService(
      paperProfileRepository,
      mock(PaperAuthorRepository.class),
      mock(AiScreeningResultRepository.class),
      mock(PaperScoreSnapshotRepository.class),
      postService
    );

    PaperProfile paper = buildPaper(
      11L,
      "Retracted Paper",
      PaperPublicationStatus.PUBLISHED,
      PostStatus.PUBLISHED
    );
    when(paperProfileRepository.findById(11L)).thenReturn(java.util.Optional.of(paper));
    when(paperProfileRepository.save(any(PaperProfile.class))).thenAnswer(invocation ->
      invocation.getArgument(0)
    );

    var result = service.retractPaper(11L);

    assertEquals(PaperPublicationStatus.RETRACTED, result.getPublicationStatus());
    org.mockito.Mockito.verify(postService).rejectPost(111L);
  }

  private PaperProfile buildPaper(
    Long id,
    String title,
    PaperPublicationStatus paperStatus,
    PostStatus postStatus
  ) {
    User submitter = new User();
    submitter.setId(7L);
    submitter.setUsername("submitter");

    Post post = new Post();
    post.setId(id + 100);
    post.setTitle(title);
    post.setContent("Paper body");
    post.setStatus(postStatus);
    post.setAuthor(submitter);

    PaperProfile paper = new PaperProfile();
    paper.setId(id);
    paper.setPost(post);
    paper.setTitle(title);
    paper.setAbstractText("Abstract");
    paper.setSubjectArea("Information Systems");
    paper.setPaperType("Research Article");
    paper.setPublicationStatus(paperStatus);
    paper.setScreeningStatus(PaperScreeningStatus.SCREENING);
    paper.setCreatedBy(submitter);
    return paper;
  }
}
