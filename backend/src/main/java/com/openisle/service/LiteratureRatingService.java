package com.openisle.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.openisle.dto.LiteratureAuthorRankingDto;
import com.openisle.dto.LiteraturePaperRankingDto;
import com.openisle.dto.LiteratureRatingRequest;
import com.openisle.dto.LiteratureRatingResponse;
import com.openisle.dto.LiteratureScoreSnapshotDto;
import com.openisle.exception.NotFoundException;
import com.openisle.model.LiteratureRating;
import com.openisle.model.LiteratureScoreSnapshot;
import com.openisle.model.User;
import com.openisle.repository.LiteratureRatingRepository;
import com.openisle.repository.LiteratureScoreSnapshotRepository;
import com.openisle.repository.UserRepository;
import com.openisle.service.LiteratureIntegrationService.LiteratureProxyResponse;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class LiteratureRatingService {

  private final LiteratureRatingRepository ratingRepository;
  private final LiteratureScoreSnapshotRepository snapshotRepository;
  private final UserRepository userRepository;
  private final LiteratureIntegrationService literatureIntegrationService;

  @Transactional
  public LiteratureRatingResponse rateLiterature(
    String username,
    Long literaturePaperId,
    LiteratureRatingRequest request
  ) {
    validateRequest(request);
    validatePaper(literaturePaperId);

    User rater = userRepository
      .findByUsername(username)
      .orElseThrow(() -> new NotFoundException("User not found"));
    LiteratureRating rating = ratingRepository
      .findByLiteraturePaperIdAndRaterId(literaturePaperId, rater.getId())
      .orElseGet(LiteratureRating::new);

    rating.setLiteraturePaperId(literaturePaperId);
    rating.setRater(rater);
    rating.setOriginalityScore(request.getOriginalityScore());
    rating.setRigorScore(request.getRigorScore());
    rating.setEvidenceScore(request.getEvidenceScore());
    rating.setSignificanceScore(request.getSignificanceScore());
    rating.setReproducibilityScore(request.getReproducibilityScore());
    rating.setClarityScore(request.getClarityScore());
    rating.setReadConfirmed(true);
    rating.setComment(request.getComment().strip());
    rating = ratingRepository.save(rating);

    return toResponse(rating, recalculateSnapshot(literaturePaperId));
  }

  @Transactional(readOnly = true)
  public LiteratureRatingResponse getMyRating(String username, Long literaturePaperId) {
    User rater = userRepository
      .findByUsername(username)
      .orElseThrow(() -> new NotFoundException("User not found"));
    LiteratureRating rating = ratingRepository
      .findByLiteraturePaperIdAndRaterId(literaturePaperId, rater.getId())
      .orElseThrow(() -> new NotFoundException("Rating not found"));
    return toResponse(rating, snapshotRepository.findByLiteraturePaperId(literaturePaperId).orElse(null));
  }

  @Transactional(readOnly = true)
  public List<LiteratureRatingResponse> listRatings(Long literaturePaperId) {
    return ratingRepository
      .findByLiteraturePaperIdOrderByUpdatedAtDesc(literaturePaperId)
      .stream()
      .map(rating -> toResponse(rating, null))
      .toList();
  }

  @Transactional(readOnly = true)
  public LiteratureScoreSnapshotDto getScoreSnapshot(Long literaturePaperId) {
    return snapshotRepository
      .findByLiteraturePaperId(literaturePaperId)
      .map(this::toSnapshotDto)
      .orElseGet(LiteratureRatingService::emptySnapshot);
  }

  @Transactional(readOnly = true)
  public List<LiteraturePaperRankingDto> rankPapers(int requestedLimit) {
    int limit = Math.max(1, Math.min(requestedLimit, 100));
    Map<Long, JsonNode> metadata = loadPaperMetadata();
    List<LiteratureScoreSnapshot> snapshots = snapshotRepository
      .findAll()
      .stream()
      .filter(snapshot -> snapshot.getRatingCount() > 0)
      .sorted(
        Comparator.comparingDouble(LiteratureScoreSnapshot::getCompositeScore)
          .reversed()
          .thenComparing(Comparator.comparingInt(LiteratureScoreSnapshot::getRatingCount).reversed())
          .thenComparing(LiteratureScoreSnapshot::getLiteraturePaperId)
      )
      .limit(limit)
      .toList();

    List<LiteraturePaperRankingDto> result = new ArrayList<>();
    for (int index = 0; index < snapshots.size(); index++) {
      LiteratureScoreSnapshot snapshot = snapshots.get(index);
      result.add(toPaperRanking(index + 1, snapshot, metadata.get(snapshot.getLiteraturePaperId())));
    }
    return result;
  }

  @Transactional(readOnly = true)
  public List<LiteratureAuthorRankingDto> rankAuthors(int requestedLimit) {
    int limit = Math.max(1, Math.min(requestedLimit, 100));
    Map<String, AuthorAggregate> aggregates = new LinkedHashMap<>();
    for (LiteraturePaperRankingDto paper : rankPapers(100)) {
      for (String author : paper.getAuthors()) {
        if (author == null || author.isBlank()) continue;
        aggregates.computeIfAbsent(author.strip(), ignored -> new AuthorAggregate()).add(paper);
      }
    }

    List<Map.Entry<String, AuthorAggregate>> sorted = aggregates
      .entrySet()
      .stream()
      .sorted(
        Comparator.<Map.Entry<String, AuthorAggregate>>comparingDouble(entry -> entry.getValue().average())
          .reversed()
          .thenComparing(Comparator.comparingInt((Map.Entry<String, AuthorAggregate> entry) -> entry.getValue().ratingCount).reversed())
          .thenComparing(Map.Entry::getKey)
      )
      .limit(limit)
      .toList();

    List<LiteratureAuthorRankingDto> result = new ArrayList<>();
    for (int index = 0; index < sorted.size(); index++) {
      Map.Entry<String, AuthorAggregate> entry = sorted.get(index);
      LiteratureAuthorRankingDto dto = new LiteratureAuthorRankingDto();
      dto.setRank(index + 1);
      dto.setAuthorName(entry.getKey());
      dto.setPaperCount(entry.getValue().paperCount);
      dto.setTotalRatingCount(entry.getValue().ratingCount);
      dto.setAverageCompositeScore(round(entry.getValue().average()));
      result.add(dto);
    }
    return result;
  }

  private void validatePaper(Long literaturePaperId) {
    if (literaturePaperId == null || literaturePaperId <= 0) {
      throw new IllegalArgumentException("literaturePaperId must be positive");
    }
    LiteratureProxyResponse response = literatureIntegrationService.getPaper(literaturePaperId);
    if (!response.status().is2xxSuccessful()) {
      throw new NotFoundException("Literature paper not found");
    }
  }

  private void validateRequest(LiteratureRatingRequest request) {
    if (request == null) throw new IllegalArgumentException("Rating request is required");
    validateScore("originalityScore", request.getOriginalityScore());
    validateScore("rigorScore", request.getRigorScore());
    validateScore("evidenceScore", request.getEvidenceScore());
    validateScore("significanceScore", request.getSignificanceScore());
    validateScore("reproducibilityScore", request.getReproducibilityScore());
    validateScore("clarityScore", request.getClarityScore());
    if (!Boolean.TRUE.equals(request.getReadConfirmed())) {
      throw new IllegalArgumentException("Reading confirmation is required");
    }
    String comment = request.getComment() == null ? "" : request.getComment().strip();
    if (comment.length() < 20 || comment.length() > 500) {
      throw new IllegalArgumentException("comment must be between 20 and 500 characters");
    }
  }

  private void validateScore(String field, Integer value) {
    if (value == null || value < 1 || value > 5) {
      throw new IllegalArgumentException(field + " must be between 1 and 5");
    }
  }

  private LiteratureScoreSnapshot recalculateSnapshot(Long literaturePaperId) {
    List<LiteratureRating> ratings = ratingRepository.findByLiteraturePaperId(literaturePaperId);
    LiteratureScoreSnapshot snapshot = snapshotRepository
      .findByLiteraturePaperId(literaturePaperId)
      .orElseGet(LiteratureScoreSnapshot::new);
    snapshot.setLiteraturePaperId(literaturePaperId);
    snapshot.setRatingCount(ratings.size());
    snapshot.setAverageOriginalityScore(average(ratings, LiteratureRating::getOriginalityScore));
    snapshot.setAverageRigorScore(average(ratings, LiteratureRating::getRigorScore));
    snapshot.setAverageEvidenceScore(average(ratings, LiteratureRating::getEvidenceScore));
    snapshot.setAverageSignificanceScore(average(ratings, LiteratureRating::getSignificanceScore));
    snapshot.setAverageReproducibilityScore(average(ratings, LiteratureRating::getReproducibilityScore));
    snapshot.setAverageClarityScore(average(ratings, LiteratureRating::getClarityScore));
    snapshot.setCompositeScore(
      round(
        (
          snapshot.getAverageOriginalityScore() +
          snapshot.getAverageRigorScore() +
          snapshot.getAverageEvidenceScore() +
          snapshot.getAverageSignificanceScore() +
          snapshot.getAverageReproducibilityScore() +
          snapshot.getAverageClarityScore()
        ) / 6.0
      )
    );
    return snapshotRepository.save(snapshot);
  }

  private double average(List<LiteratureRating> ratings, ScoreReader reader) {
    if (ratings.isEmpty()) return 0;
    return round(ratings.stream().mapToInt(reader::read).average().orElse(0));
  }

  private Map<Long, JsonNode> loadPaperMetadata() {
    LiteratureProxyResponse response = literatureIntegrationService.listPapers(null, "year_desc", 100, 0);
    Map<Long, JsonNode> result = new HashMap<>();
    if (!response.status().is2xxSuccessful()) return result;
    JsonNode papers = response.body().path("papers");
    if (!papers.isArray()) return result;
    papers.forEach(paper -> {
      if (paper.path("id").canConvertToLong()) result.put(paper.path("id").asLong(), paper);
    });
    return result;
  }

  private LiteraturePaperRankingDto toPaperRanking(
    int rank,
    LiteratureScoreSnapshot snapshot,
    JsonNode metadata
  ) {
    LiteraturePaperRankingDto dto = new LiteraturePaperRankingDto();
    dto.setRank(rank);
    dto.setLiteraturePaperId(snapshot.getLiteraturePaperId());
    dto.setRatingCount(snapshot.getRatingCount());
    dto.setCompositeScore(snapshot.getCompositeScore());
    dto.setScoreSnapshot(toSnapshotDto(snapshot));
    dto.setTitle(metadata == null ? "Literature record " + snapshot.getLiteraturePaperId() : metadata.path("title").asText());
    if (metadata != null) {
      dto.setJournal(metadata.path("journal").asText(null));
      dto.setYear(metadata.path("year").isNumber() ? metadata.path("year").asInt() : null);
      JsonNode authors = metadata.path("author");
      if (authors.isArray()) authors.forEach(author -> dto.getAuthors().add(author.asText()));
    }
    return dto;
  }

  private LiteratureRatingResponse toResponse(
    LiteratureRating rating,
    LiteratureScoreSnapshot snapshot
  ) {
    LiteratureRatingResponse dto = new LiteratureRatingResponse();
    dto.setRatingId(rating.getId());
    dto.setLiteraturePaperId(rating.getLiteraturePaperId());
    dto.setRaterId(rating.getRater().getId());
    dto.setRaterUsername(rating.getRater().getUsername());
    dto.setOriginalityScore(rating.getOriginalityScore());
    dto.setRigorScore(rating.getRigorScore());
    dto.setEvidenceScore(rating.getEvidenceScore());
    dto.setSignificanceScore(rating.getSignificanceScore());
    dto.setReproducibilityScore(rating.getReproducibilityScore());
    dto.setClarityScore(rating.getClarityScore());
    dto.setComment(rating.getComment());
    dto.setUpdatedAt(rating.getUpdatedAt());
    dto.setScoreSnapshot(snapshot == null ? null : toSnapshotDto(snapshot));
    return dto;
  }

  private LiteratureScoreSnapshotDto toSnapshotDto(LiteratureScoreSnapshot snapshot) {
    LiteratureScoreSnapshotDto dto = new LiteratureScoreSnapshotDto();
    dto.setRatingCount(snapshot.getRatingCount());
    dto.setAverageOriginalityScore(snapshot.getAverageOriginalityScore());
    dto.setAverageRigorScore(snapshot.getAverageRigorScore());
    dto.setAverageEvidenceScore(snapshot.getAverageEvidenceScore());
    dto.setAverageSignificanceScore(snapshot.getAverageSignificanceScore());
    dto.setAverageReproducibilityScore(snapshot.getAverageReproducibilityScore());
    dto.setAverageClarityScore(snapshot.getAverageClarityScore());
    dto.setCompositeScore(snapshot.getCompositeScore());
    return dto;
  }

  private static LiteratureScoreSnapshotDto emptySnapshot() {
    return new LiteratureScoreSnapshotDto();
  }

  private double round(double value) {
    return Math.round(value * 100.0) / 100.0;
  }

  @FunctionalInterface
  private interface ScoreReader {
    int read(LiteratureRating rating);
  }

  private static class AuthorAggregate {
    private int paperCount;
    private int ratingCount;
    private double compositeTotal;

    private void add(LiteraturePaperRankingDto paper) {
      paperCount++;
      ratingCount += paper.getRatingCount();
      compositeTotal += paper.getCompositeScore();
    }

    private double average() {
      return paperCount == 0 ? 0 : compositeTotal / paperCount;
    }
  }
}
