package com.openisle.service;

import com.openisle.dto.AuthorRankingDto;
import com.openisle.dto.InstitutionRankingDto;
import com.openisle.dto.PaperRankingDto;
import com.openisle.model.PaperAuthor;
import com.openisle.model.PaperPublicationStatus;
import com.openisle.model.PaperScoreSnapshot;
import com.openisle.repository.PaperAuthorRepository;
import com.openisle.repository.PaperScoreSnapshotRepository;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class PaperRankingService {

  private final PaperScoreSnapshotRepository paperScoreSnapshotRepository;
  private final PaperAuthorRepository paperAuthorRepository;
  private final PaperAccessPolicy paperAccessPolicy;

  @Transactional(readOnly = true)
  public List<PaperRankingDto> listTopPapers(int limit) {
    List<PaperScoreSnapshot> snapshots =
      paperScoreSnapshotRepository.findByRatingCountGreaterThanAndPaperPublicationStatusOrderByCompositeScoreDesc(
        0,
        PaperPublicationStatus.PUBLISHED,
        PageRequest.of(0, normalizedLimit(limit))
      );
    return rankPapers(snapshots.stream().filter(snapshot -> paperAccessPolicy.canEnterRanking(snapshot.getPaper())).toList());
  }

  @Transactional(readOnly = true)
  public List<AuthorRankingDto> listAuthorRankings(int limit) {
    Map<String, RankingAccumulator> accumulators = new HashMap<>();
    for (PaperScoreSnapshot snapshot : paperScoreSnapshotRepository.findByRatingCountGreaterThanAndPaperPublicationStatus(
      0,
      PaperPublicationStatus.PUBLISHED
    )) {
      if (!paperAccessPolicy.canEnterRanking(snapshot.getPaper())) {
        continue;
      }
      List<PaperAuthor> authors = paperAuthorRepository.findByPaperIdOrderByAuthorOrderAsc(
        snapshot.getPaper().getId()
      );
      for (PaperAuthor author : authors) {
        if (author.getDisplayName() == null || author.getDisplayName().isBlank()) {
          continue;
        }
        accumulators
          .computeIfAbsent(author.getDisplayName(), RankingAccumulator::new)
          .add(snapshot);
      }
    }

    AtomicInteger rank = new AtomicInteger(1);
    return accumulators
      .values()
      .stream()
      .sorted(RankingAccumulator.ORDER)
      .limit(normalizedLimit(limit))
      .peek(accumulator -> accumulator.rank = rank.getAndIncrement())
      .map(PaperRankingService::toAuthorDto)
      .toList();
  }

  @Transactional(readOnly = true)
  public List<InstitutionRankingDto> listInstitutionRankings(int limit) {
    Map<String, RankingAccumulator> accumulators = new HashMap<>();
    for (PaperScoreSnapshot snapshot : paperScoreSnapshotRepository.findByRatingCountGreaterThanAndPaperPublicationStatus(
      0,
      PaperPublicationStatus.PUBLISHED
    )) {
      if (!paperAccessPolicy.canEnterRanking(snapshot.getPaper())) {
        continue;
      }
      List<PaperAuthor> authors = paperAuthorRepository.findByPaperIdOrderByAuthorOrderAsc(
        snapshot.getPaper().getId()
      );
      for (PaperAuthor author : authors) {
        if (author.getInstitution() == null || author.getInstitution().getName() == null) {
          continue;
        }
        String institutionName = author.getInstitution().getName();
        if (institutionName.isBlank()) {
          continue;
        }
        accumulators.computeIfAbsent(institutionName, RankingAccumulator::new).add(snapshot);
      }
    }

    AtomicInteger rank = new AtomicInteger(1);
    return accumulators
      .values()
      .stream()
      .sorted(RankingAccumulator.ORDER)
      .limit(normalizedLimit(limit))
      .peek(accumulator -> accumulator.rank = rank.getAndIncrement())
      .map(PaperRankingService::toInstitutionDto)
      .toList();
  }

  private List<PaperRankingDto> rankPapers(List<PaperScoreSnapshot> snapshots) {
    List<PaperRankingDto> result = new ArrayList<>();
    for (int i = 0; i < snapshots.size(); i++) {
      result.add(toPaperDto(i + 1, snapshots.get(i)));
    }
    return result;
  }

  private static PaperRankingDto toPaperDto(int rank, PaperScoreSnapshot snapshot) {
    PaperRankingDto dto = new PaperRankingDto();
    dto.setRank(rank);
    dto.setPaperId(snapshot.getPaper().getId());
    dto.setPostId(snapshot.getPaper().getPost().getId());
    dto.setTitle(snapshot.getPaper().getTitle());
    dto.setSubjectArea(snapshot.getPaper().getSubjectArea());
    dto.setRatingCount(snapshot.getRatingCount());
    dto.setAverageOverallScore(snapshot.getAverageOverallScore());
    dto.setCompositeScore(snapshot.getCompositeScore());
    return dto;
  }

  private static AuthorRankingDto toAuthorDto(RankingAccumulator accumulator) {
    AuthorRankingDto dto = new AuthorRankingDto();
    dto.setRank(accumulator.rank);
    dto.setAuthorName(accumulator.name);
    dto.setPaperCount(accumulator.paperCount);
    dto.setTotalRatingCount(accumulator.totalRatingCount);
    dto.setAverageCompositeScore(accumulator.averageCompositeScore());
    return dto;
  }

  private static InstitutionRankingDto toInstitutionDto(RankingAccumulator accumulator) {
    InstitutionRankingDto dto = new InstitutionRankingDto();
    dto.setRank(accumulator.rank);
    dto.setInstitutionName(accumulator.name);
    dto.setPaperCount(accumulator.paperCount);
    dto.setTotalRatingCount(accumulator.totalRatingCount);
    dto.setAverageCompositeScore(accumulator.averageCompositeScore());
    return dto;
  }

  private int normalizedLimit(int limit) {
    return Math.min(Math.max(limit, 1), 100);
  }

  private static class RankingAccumulator {

    private static final Comparator<RankingAccumulator> ORDER = Comparator
      .comparingDouble(RankingAccumulator::averageCompositeScore)
      .reversed()
      .thenComparing(Comparator.comparingInt((RankingAccumulator a) -> a.totalRatingCount).reversed())
      .thenComparing(a -> a.name);

    private final String name;
    private int paperCount;
    private int totalRatingCount;
    private double totalCompositeScore;
    private int rank;

    private RankingAccumulator(String name) {
      this.name = name;
    }

    private void add(PaperScoreSnapshot snapshot) {
      paperCount++;
      totalRatingCount += snapshot.getRatingCount();
      totalCompositeScore += snapshot.getCompositeScore();
    }

    private double averageCompositeScore() {
      if (paperCount == 0) {
        return 0;
      }
      return Math.round((totalCompositeScore / paperCount) * 100.0) / 100.0;
    }
  }
}
