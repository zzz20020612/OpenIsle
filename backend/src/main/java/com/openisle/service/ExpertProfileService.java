package com.openisle.service;

import com.openisle.dto.ExpertPaperDto;
import com.openisle.dto.ExpertProfileDto;
import com.openisle.dto.PaperScoreSnapshotDto;
import com.openisle.exception.NotFoundException;
import com.openisle.model.ExpertProfile;
import com.openisle.model.PaperAuthor;
import com.openisle.model.PaperProfile;
import com.openisle.model.PaperScoreSnapshot;
import com.openisle.repository.ExpertProfileRepository;
import com.openisle.repository.PaperAuthorRepository;
import com.openisle.repository.PaperScoreSnapshotRepository;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class ExpertProfileService {

  private final ExpertProfileRepository expertProfileRepository;
  private final PaperAuthorRepository paperAuthorRepository;
  private final PaperScoreSnapshotRepository paperScoreSnapshotRepository;
  private final PaperAccessPolicy paperAccessPolicy;

  @Transactional(readOnly = true)
  public ExpertProfileDto getExpert(Long expertId) {
    ExpertProfile expert = expertProfileRepository
      .findById(expertId)
      .orElseThrow(() -> new NotFoundException("Expert not found"));
    List<ExpertPaperDto> papers = paperAuthorRepository
      .findByExpertProfileIdOrderByPaperPublishedAtDescAuthorOrderAsc(expertId)
      .stream()
      .filter(author -> paperAccessPolicy.canAppearInFeed(author.getPaper()))
      .map(this::toPaperDto)
      .toList();

    ExpertProfileDto dto = new ExpertProfileDto();
    dto.setId(expert.getId());
    dto.setUserId(expert.getUser() != null ? expert.getUser().getId() : null);
    dto.setDisplayName(expert.getDisplayName());
    dto.setEmail(expert.getEmail());
    dto.setOrcid(expert.getOrcid());
    dto.setPrimaryInstitutionId(
      expert.getPrimaryInstitution() != null ? expert.getPrimaryInstitution().getId() : null
    );
    dto.setPrimaryInstitutionName(
      expert.getPrimaryInstitution() != null ? expert.getPrimaryInstitution().getName() : null
    );
    dto.setCountry(expert.getCountry());
    dto.setIdentityStatus(expert.getIdentityStatus());
    dto.setPaperCount(papers.size());
    dto.setPapers(papers);
    return dto;
  }

  private ExpertPaperDto toPaperDto(PaperAuthor author) {
    PaperProfile paper = author.getPaper();
    ExpertPaperDto dto = new ExpertPaperDto();
    dto.setPaperId(paper.getId());
    dto.setPostId(paper.getPost() != null ? paper.getPost().getId() : null);
    dto.setTitle(paper.getTitle());
    dto.setSubjectArea(paper.getSubjectArea());
    dto.setAuthorOrder(author.getAuthorOrder());
    dto.setCorrespondingAuthor(author.isCorrespondingAuthor());
    dto.setEqualContribution(author.isEqualContribution());
    dto.setAuthorRole(resolveAuthorRole(author));
    dto.setPublishedAt(paper.getPublishedAt());
    dto.setScoreSnapshot(
      paperScoreSnapshotRepository.findByPaperId(paper.getId()).map(this::toScoreDto).orElseGet(PaperScoreSnapshotDto::new)
    );
    return dto;
  }

  private String resolveAuthorRole(PaperAuthor author) {
    if (author.isCorrespondingAuthor() && author.isEqualContribution()) {
      return "Co-first and corresponding author";
    }
    if (author.isCorrespondingAuthor()) {
      return "Corresponding author";
    }
    if (author.isEqualContribution()) {
      return "Co-first author";
    }
    return "Author";
  }

  private PaperScoreSnapshotDto toScoreDto(PaperScoreSnapshot snapshot) {
    PaperScoreSnapshotDto dto = new PaperScoreSnapshotDto();
    dto.setRatingCount(snapshot.getRatingCount());
    dto.setAverageOverallScore(snapshot.getAverageOverallScore());
    dto.setAverageInnovationScore(snapshot.getAverageInnovationScore());
    dto.setAverageMethodScore(snapshot.getAverageMethodScore());
    dto.setAverageImpactScore(snapshot.getAverageImpactScore());
    dto.setCompositeScore(snapshot.getCompositeScore());
    return dto;
  }
}
