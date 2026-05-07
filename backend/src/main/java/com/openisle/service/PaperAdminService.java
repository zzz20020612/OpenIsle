package com.openisle.service;

import com.openisle.dto.AiScreeningDto;
import com.openisle.dto.PaperAdminSummaryDto;
import com.openisle.dto.PaperAuthorDto;
import com.openisle.dto.PaperScoreSnapshotDto;
import com.openisle.exception.NotFoundException;
import com.openisle.model.AiScreeningResult;
import com.openisle.model.PaperAuthor;
import com.openisle.model.PaperProfile;
import com.openisle.model.PaperPublicationStatus;
import com.openisle.model.PaperScoreSnapshot;
import com.openisle.model.PaperScreeningStatus;
import com.openisle.repository.AiScreeningResultRepository;
import com.openisle.repository.PaperAuthorRepository;
import com.openisle.repository.PaperProfileRepository;
import com.openisle.repository.PaperScoreSnapshotRepository;
import java.util.List;
import java.util.Objects;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class PaperAdminService {

  private final PaperProfileRepository paperProfileRepository;
  private final PaperAuthorRepository paperAuthorRepository;
  private final AiScreeningResultRepository aiScreeningResultRepository;
  private final PaperScoreSnapshotRepository paperScoreSnapshotRepository;
  private final PostService postService;

  @Transactional(readOnly = true)
  public List<PaperAdminSummaryDto> listPapers(
    int page,
    int pageSize,
    PaperPublicationStatus status
  ) {
    PageRequest pageRequest = PageRequest.of(
      Math.max(page, 0),
      Math.max(pageSize, 1),
      Sort.by(Sort.Direction.DESC, "createdAt")
    );
    List<PaperProfile> papers = status == null
      ? paperProfileRepository.findAll(pageRequest).getContent()
      : paperProfileRepository.findByPublicationStatusOrderByCreatedAtDesc(status, pageRequest);

    return papers.stream().map(this::toAdminSummaryDto).toList();
  }

  @Transactional(readOnly = true)
  public PaperAdminSummaryDto getPaper(Long paperId) {
    return toAdminSummaryDto(getPaperOrThrow(paperId));
  }

  @Transactional
  public PaperAdminSummaryDto retractPaper(Long paperId) {
    PaperProfile paper = getPaperOrThrow(paperId);
    paper.setPublicationStatus(PaperPublicationStatus.RETRACTED);
    postService.rejectPost(paper.getPost().getId());
    return toAdminSummaryDto(paperProfileRepository.save(paper));
  }

  private PaperProfile getPaperOrThrow(Long paperId) {
    return paperProfileRepository
      .findById(paperId)
      .orElseThrow(() -> new NotFoundException("Paper not found"));
  }

  private PaperAdminSummaryDto toAdminSummaryDto(PaperProfile paper) {
    PaperAdminSummaryDto dto = new PaperAdminSummaryDto();
    dto.setId(paper.getId());
    dto.setPostId(paper.getPost().getId());
    dto.setTitle(paper.getTitle());
    dto.setAbstractText(paper.getAbstractText());
    dto.setKeywords(deserializeList(paper.getKeywords()));
    dto.setSubjectArea(paper.getSubjectArea());
    dto.setPaperType(paper.getPaperType());
    dto.setPublicationStatus(paper.getPublicationStatus());
    dto.setScreeningStatus(paper.getScreeningStatus());
    dto.setPrimaryInstitutionName(
      paper.getPrimaryInstitution() != null ? paper.getPrimaryInstitution().getName() : null
    );
    dto.setAuthors(
      paperAuthorRepository
        .findByPaperIdOrderByAuthorOrderAsc(paper.getId())
        .stream()
        .map(this::toAuthorDto)
        .toList()
    );
    dto.setSubmitterUsername(
      paper.getCreatedBy() != null ? paper.getCreatedBy().getUsername() : null
    );
    dto.setPostStatus(paper.getPost().getStatus());
    dto.setDiscussionClosed(paper.getPost().isClosed());
    dto.setPinned(paper.getPost().getPinnedAt() != null);
    dto.setRssExcluded(Boolean.TRUE.equals(paper.getPost().getRssExcluded()));
    dto.setCreatedAt(paper.getCreatedAt());
    dto.setPublishedAt(paper.getPublishedAt());
    dto.setScoreSnapshot(getScoreSnapshotDto(paper.getId()));
    dto.setScreening(getLatestScreeningDto(paper.getId()));
    return dto;
  }

  private AiScreeningDto getLatestScreeningDto(Long paperId) {
    return aiScreeningResultRepository
      .findFirstByPaperIdOrderByScreenedAtDesc(paperId)
      .map(this::toScreeningDto)
      .orElse(null);
  }

  private PaperAuthorDto toAuthorDto(PaperAuthor author) {
    PaperAuthorDto dto = new PaperAuthorDto();
    dto.setId(author.getId());
    dto.setAuthorOrder(author.getAuthorOrder());
    dto.setDisplayName(author.getDisplayName());
    dto.setInstitutionId(author.getInstitution() != null ? author.getInstitution().getId() : null);
    dto.setInstitution(author.getInstitution() != null ? author.getInstitution().getName() : null);
    dto.setCountry(author.getCountry());
    dto.setCorrespondingAuthor(author.isCorrespondingAuthor());
    dto.setEqualContribution(author.isEqualContribution());
    dto.setIdentityStatus(author.getIdentityStatus());
    dto.setExpertProfileId(
      author.getExpertProfile() != null ? author.getExpertProfile().getId() : null
    );
    dto.setUserId(author.getUser() != null ? author.getUser().getId() : null);
    return dto;
  }

  private AiScreeningDto toScreeningDto(AiScreeningResult screening) {
    AiScreeningDto dto = new AiScreeningDto();
    dto.setStatus(screening.getStatus());
    dto.setRiskLevel(screening.getRiskLevel());
    dto.setDetectedSubjectArea(screening.getDetectedSubjectArea());
    dto.setDetectedPaperType(screening.getDetectedPaperType());
    dto.setSummary(screening.getSummary());
    dto.setIssuesJson(screening.getIssuesJson());
    dto.setScreenedAt(screening.getScreenedAt());
    return dto;
  }

  private PaperScoreSnapshotDto getScoreSnapshotDto(Long paperId) {
    return paperScoreSnapshotRepository
      .findByPaperId(paperId)
      .map(this::toScoreSnapshotDto)
      .orElseGet(PaperScoreSnapshotDto::new);
  }

  private PaperScoreSnapshotDto toScoreSnapshotDto(PaperScoreSnapshot snapshot) {
    PaperScoreSnapshotDto dto = new PaperScoreSnapshotDto();
    dto.setRatingCount(snapshot.getRatingCount());
    dto.setAverageOverallScore(snapshot.getAverageOverallScore());
    dto.setAverageInnovationScore(snapshot.getAverageInnovationScore());
    dto.setAverageMethodScore(snapshot.getAverageMethodScore());
    dto.setAverageImpactScore(snapshot.getAverageImpactScore());
    dto.setCompositeScore(snapshot.getCompositeScore());
    return dto;
  }

  private static List<String> deserializeList(String value) {
    if (value == null || value.isBlank()) {
      return List.of();
    }
    return value
      .lines()
      .map(String::trim)
      .filter(line -> !line.isBlank())
      .toList();
  }
}
