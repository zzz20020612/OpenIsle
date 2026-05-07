package com.openisle.service;

import com.openisle.model.PaperAuthor;
import com.openisle.model.PaperProfile;
import com.openisle.model.PaperPublicationStatus;
import com.openisle.model.User;
import com.openisle.repository.PaperAuthorRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class PaperAccessPolicy {

  private final PaperAuthorRepository paperAuthorRepository;

  public boolean canAppearInFeed(PaperProfile paper) {
    return isPublished(paper);
  }

  public boolean canEnterRanking(PaperProfile paper) {
    return isPublished(paper);
  }

  public boolean canRatePaper(User user, PaperProfile paper) {
    return user != null && isPublished(paper) && !isPaperAuthor(user, paper);
  }

  public boolean isPaperAuthor(User user, PaperProfile paper) {
    if (user == null || paper == null || user.getId() == null) {
      return false;
    }
    if (
      paper.getCreatedBy() != null &&
      paper.getCreatedBy().getId() != null &&
      paper.getCreatedBy().getId().equals(user.getId())
    ) {
      return true;
    }
    if (paper.getId() == null) {
      return false;
    }
    return paperAuthorRepository
      .findByPaperIdOrderByAuthorOrderAsc(paper.getId())
      .stream()
      .map(PaperAuthor::getUser)
      .anyMatch(authorUser ->
        authorUser != null && authorUser.getId() != null && authorUser.getId().equals(user.getId())
      );
  }

  private boolean isPublished(PaperProfile paper) {
    return paper != null && paper.getPublicationStatus() == PaperPublicationStatus.PUBLISHED;
  }
}
