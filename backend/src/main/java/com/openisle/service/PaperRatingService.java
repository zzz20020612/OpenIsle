package com.openisle.service;

import com.openisle.dto.PaperRatingRequest;
import com.openisle.dto.PaperRatingResponse;
import com.openisle.dto.PaperScoreSnapshotDto;
import com.openisle.exception.NotFoundException;
import com.openisle.model.PaperProfile;
import com.openisle.model.PaperRating;
import com.openisle.model.PaperScoreSnapshot;
import com.openisle.model.User;
import com.openisle.repository.PaperProfileRepository;
import com.openisle.repository.PaperRatingRepository;
import com.openisle.repository.PaperScoreSnapshotRepository;
import com.openisle.repository.UserRepository;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class PaperRatingService {

  private final PaperProfileRepository paperProfileRepository;
  private final PaperRatingRepository paperRatingRepository;
  private final PaperScoreSnapshotRepository paperScoreSnapshotRepository;
  private final UserRepository userRepository;
  private final PaperAccessPolicy paperAccessPolicy;

  @Transactional
  public PaperRatingResponse ratePaper(String username, Long paperId, PaperRatingRequest request) {
    validateRequest(request);

    User rater = userRepository
      .findByUsername(username)
      .orElseThrow(() -> new NotFoundException("User not found"));
    PaperProfile paper = paperProfileRepository
      .findById(paperId)
      .orElseThrow(() -> new NotFoundException("Paper not found"));
    if (paperAccessPolicy.isPaperAuthor(rater, paper)) {
      throw new IllegalArgumentException("Authors cannot rate their own papers");
    }
    if (!paperAccessPolicy.canRatePaper(rater, paper)) {
      throw new IllegalArgumentException("This paper is not eligible for rating");
    }

    PaperRating rating = paperRatingRepository
      .findByPaperIdAndRaterId(paperId, rater.getId())
      .orElseGet(PaperRating::new);
    rating.setPaper(paper);
    rating.setRater(rater);
    rating.setOverallScore(request.getOverallScore());
    rating.setInnovationScore(request.getInnovationScore());
    rating.setMethodScore(request.getMethodScore());
    rating.setImpactScore(request.getImpactScore());
    rating.setComment(request.getComment());
    rating = paperRatingRepository.save(rating);

    PaperScoreSnapshot snapshot = recalculateSnapshot(paper);
    return toResponse(rating, snapshot);
  }

  @Transactional(readOnly = true)
  public PaperRatingResponse getMyRating(String username, Long paperId) {
    User rater = userRepository
      .findByUsername(username)
      .orElseThrow(() -> new NotFoundException("User not found"));
    PaperRating rating = paperRatingRepository
      .findByPaperIdAndRaterId(paperId, rater.getId())
      .orElseThrow(() -> new NotFoundException("Rating not found"));
    PaperScoreSnapshot snapshot = paperScoreSnapshotRepository
      .findByPaperId(paperId)
      .orElse(null);
    return toResponse(rating, snapshot);
  }

  @Transactional(readOnly = true)
  public PaperScoreSnapshotDto getScoreSnapshot(Long paperId) {
    return paperScoreSnapshotRepository
      .findByPaperId(paperId)
      .map(this::toSnapshotDto)
      .orElseGet(PaperRatingService::emptySnapshotDto);
  }

  private PaperScoreSnapshot recalculateSnapshot(PaperProfile paper) {
    List<PaperRating> ratings = paperRatingRepository.findByPaperId(paper.getId());
    PaperScoreSnapshot snapshot = paperScoreSnapshotRepository
      .findByPaperId(paper.getId())
      .orElseGet(PaperScoreSnapshot::new);
    snapshot.setPaper(paper);
    snapshot.setRatingCount(ratings.size());

    if (ratings.isEmpty()) {
      snapshot.setAverageOverallScore(0);
      snapshot.setAverageInnovationScore(0);
      snapshot.setAverageMethodScore(0);
      snapshot.setAverageImpactScore(0);
      snapshot.setCompositeScore(0);
      return paperScoreSnapshotRepository.save(snapshot);
    }

    double averageOverall = average(ratings.stream().mapToInt(PaperRating::getOverallScore).sum(), ratings.size());
    double averageInnovation = average(
      ratings.stream().mapToInt(PaperRating::getInnovationScore).sum(),
      ratings.size()
    );
    double averageMethod = average(ratings.stream().mapToInt(PaperRating::getMethodScore).sum(), ratings.size());
    double averageImpact = average(ratings.stream().mapToInt(PaperRating::getImpactScore).sum(), ratings.size());

    snapshot.setAverageOverallScore(averageOverall);
    snapshot.setAverageInnovationScore(averageInnovation);
    snapshot.setAverageMethodScore(averageMethod);
    snapshot.setAverageImpactScore(averageImpact);
    snapshot.setCompositeScore(average((averageOverall + averageInnovation + averageMethod + averageImpact), 4));
    return paperScoreSnapshotRepository.save(snapshot);
  }

  private void validateRequest(PaperRatingRequest request) {
    if (request == null) {
      throw new IllegalArgumentException("Rating request is required");
    }
    validateScore("overallScore", request.getOverallScore());
    validateScore("innovationScore", request.getInnovationScore());
    validateScore("methodScore", request.getMethodScore());
    validateScore("impactScore", request.getImpactScore());
  }

  private void validateScore(String field, Integer score) {
    if (score == null || score < 1 || score > 5) {
      throw new IllegalArgumentException(field + " must be between 1 and 5");
    }
  }

  private double average(double total, int count) {
    return Math.round((total / count) * 100.0) / 100.0;
  }

  private PaperRatingResponse toResponse(PaperRating rating, PaperScoreSnapshot snapshot) {
    PaperRatingResponse response = new PaperRatingResponse();
    response.setRatingId(rating.getId());
    response.setPaperId(rating.getPaper().getId());
    response.setRaterId(rating.getRater().getId());
    response.setOverallScore(rating.getOverallScore());
    response.setInnovationScore(rating.getInnovationScore());
    response.setMethodScore(rating.getMethodScore());
    response.setImpactScore(rating.getImpactScore());
    response.setComment(rating.getComment());
    response.setUpdatedAt(rating.getUpdatedAt());
    response.setScoreSnapshot(snapshot != null ? toSnapshotDto(snapshot) : emptySnapshotDto());
    return response;
  }

  private PaperScoreSnapshotDto toSnapshotDto(PaperScoreSnapshot snapshot) {
    PaperScoreSnapshotDto dto = new PaperScoreSnapshotDto();
    dto.setRatingCount(snapshot.getRatingCount());
    dto.setAverageOverallScore(snapshot.getAverageOverallScore());
    dto.setAverageInnovationScore(snapshot.getAverageInnovationScore());
    dto.setAverageMethodScore(snapshot.getAverageMethodScore());
    dto.setAverageImpactScore(snapshot.getAverageImpactScore());
    dto.setCompositeScore(snapshot.getCompositeScore());
    return dto;
  }

  private static PaperScoreSnapshotDto emptySnapshotDto() {
    return new PaperScoreSnapshotDto();
  }
}
