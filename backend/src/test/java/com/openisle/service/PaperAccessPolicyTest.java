package com.openisle.service;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.openisle.model.PaperAuthor;
import com.openisle.model.PaperProfile;
import com.openisle.model.PaperPublicationStatus;
import com.openisle.model.User;
import com.openisle.repository.PaperAuthorRepository;
import java.util.List;
import org.junit.jupiter.api.Test;

class PaperAccessPolicyTest {

  @Test
  void onlyPublishedPapersCanAppearInPublicFeedAndRankings() {
    PaperAccessPolicy policy = new PaperAccessPolicy(mock(PaperAuthorRepository.class));

    assertTrue(policy.canAppearInFeed(paper(PaperPublicationStatus.PUBLISHED)));
    assertTrue(policy.canEnterRanking(paper(PaperPublicationStatus.PUBLISHED)));

    assertFalse(policy.canAppearInFeed(paper(PaperPublicationStatus.DRAFT)));
    assertFalse(policy.canEnterRanking(paper(PaperPublicationStatus.SCREENING)));
    assertFalse(policy.canAppearInFeed(paper(PaperPublicationStatus.WITHDRAWN)));
    assertFalse(policy.canEnterRanking(paper(PaperPublicationStatus.RETRACTED)));
  }

  @Test
  void paperCreatorAndLinkedCoAuthorCannotRatePublishedPaper() {
    PaperAuthorRepository paperAuthorRepository = mock(PaperAuthorRepository.class);
    PaperAccessPolicy policy = new PaperAccessPolicy(paperAuthorRepository);

    User creator = user(1L);
    User coAuthor = user(2L);
    User reader = user(3L);
    PaperProfile paper = paper(PaperPublicationStatus.PUBLISHED);
    paper.setId(10L);
    paper.setCreatedBy(creator);

    PaperAuthor authorRecord = new PaperAuthor();
    authorRecord.setUser(coAuthor);
    when(paperAuthorRepository.findByPaperIdOrderByAuthorOrderAsc(10L)).thenReturn(List.of(authorRecord));

    assertFalse(policy.canRatePaper(creator, paper));
    assertFalse(policy.canRatePaper(coAuthor, paper));
    assertTrue(policy.canRatePaper(reader, paper));
  }

  @Test
  void authorsCanViewTheirScreeningPaperButOtherUsersCannot() {
    PaperAccessPolicy policy = new PaperAccessPolicy(mock(PaperAuthorRepository.class));
    User creator = user(1L);
    PaperProfile paper = paper(PaperPublicationStatus.SCREENING);
    paper.setCreatedBy(creator);

    assertTrue(policy.canViewDetail(creator, paper));
    assertFalse(policy.canViewDetail(user(2L), paper));
  }

  @Test
  void unpublishedPapersCannotBeRatedEvenByNormalReader() {
    PaperAccessPolicy policy = new PaperAccessPolicy(mock(PaperAuthorRepository.class));

    assertFalse(policy.canRatePaper(user(3L), paper(PaperPublicationStatus.SCREENING)));
    assertFalse(policy.canRatePaper(user(3L), paper(PaperPublicationStatus.REJECTED)));
  }

  private PaperProfile paper(PaperPublicationStatus status) {
    PaperProfile paper = new PaperProfile();
    paper.setPublicationStatus(status);
    return paper;
  }

  private User user(Long id) {
    User user = new User();
    user.setId(id);
    user.setUsername("user" + id);
    return user;
  }
}
