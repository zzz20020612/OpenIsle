package com.openisle.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.openisle.dto.LiteratureConflictDeclarationRequest;
import com.openisle.dto.LiteratureReviewTaskDto;
import com.openisle.dto.LiteratureReviewerProfileDto;
import com.openisle.exception.NotFoundException;
import com.openisle.model.LiteratureReviewTask;
import com.openisle.model.LiteratureReviewTaskStatus;
import com.openisle.model.LiteratureReviewerProfile;
import com.openisle.model.User;
import com.openisle.repository.LiteratureRatingRepository;
import com.openisle.repository.LiteratureReviewTaskRepository;
import com.openisle.repository.LiteratureReviewerProfileRepository;
import com.openisle.repository.UserRepository;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class LiteratureReviewTaskService {

  private static final int TASK_DAYS = 7;
  private static final int ON_TIME_POINTS = 20;
  private static final int LATE_POINTS = 10;

  private final LiteratureReviewTaskRepository taskRepository;
  private final LiteratureReviewerProfileRepository profileRepository;
  private final LiteratureRatingRepository ratingRepository;
  private final UserRepository userRepository;
  private final LiteratureIntegrationService literatureIntegrationService;

  @Transactional(readOnly = true)
  public List<LiteratureReviewTaskDto> available(String username, int requestedLimit) {
    User user = user(username);
    int limit = Math.max(1, Math.min(requestedLimit, 50));
    JsonNode papers = literatureIntegrationService.listPapers(null, "year_desc", 100, 0).body().path("papers");
    List<LiteratureReviewTaskDto> result = new ArrayList<>();
    if (!papers.isArray()) return result;
    for (JsonNode paper : papers) {
      if (result.size() >= limit) break;
      long paperId = paper.path("id").asLong(0);
      if (paperId <= 0 || !"complete".equals(paper.path("completeness").path("state").asText())) continue;
      if (taskRepository.findByLiteraturePaperIdAndReviewerId(paperId, user.getId()).isPresent()) continue;
      if (ratingRepository.existsByLiteraturePaperIdAndRaterId(paperId, user.getId())) continue;
      result.add(fromPaper(paper));
    }
    return result;
  }

  @Transactional
  public LiteratureReviewTaskDto claim(String username, Long paperId, LiteratureConflictDeclarationRequest declaration) {
    User user = user(username);
    LiteratureReviewerProfile profile = profile(user);
    if (!profile.isEligible()) throw new IllegalArgumentException("Your reviewer qualification is currently unavailable");
    validateDeclaration(declaration);
    if (taskRepository.findByLiteraturePaperIdAndReviewerId(paperId, user.getId()).isPresent()) {
      throw new IllegalArgumentException("This review task has already been claimed");
    }
    if (ratingRepository.existsByLiteraturePaperIdAndRaterId(paperId, user.getId())) {
      throw new IllegalArgumentException("You have already evaluated this paper");
    }
    if (paperId == null || paperId <= 0) throw new NotFoundException("Literature paper not found");
    JsonNode paper = literatureIntegrationService.getPaper(paperId).body();
    if (!paper.path("id").canConvertToLong()) {
      throw new NotFoundException("Literature paper not found");
    }
    if (!"complete".equals(paper.path("completeness").path("state").asText())) {
      throw new IllegalArgumentException("Only complete literature records can be claimed");
    }

    LocalDateTime now = LocalDateTime.now();
    LiteratureReviewTask task = new LiteratureReviewTask();
    task.setLiteraturePaperId(paperId);
    task.setTitle(limit(paper.path("title").asText("Literature record " + paperId), 500));
    task.setAuthors(limit(authors(paper.path("author")), 500));
    task.setJournal(limit(paper.path("journal").asText(null), 255));
    task.setPublicationYear(publicationYear(paper));
    task.setReviewer(user);
    task.setStatus(LiteratureReviewTaskStatus.ACCEPTED);
    task.setConflictDeclared(true);
    task.setClaimedAt(now);
    task.setDueAt(now.plusDays(TASK_DAYS));
    task.setAwardedPoints(0);
    task = taskRepository.save(task);

    profile.setAcceptedTasks(profile.getAcceptedTasks() + 1);
    profileRepository.save(profile);
    return toDto(task);
  }

  @Transactional
  public List<LiteratureReviewTaskDto> mine(String username) {
    User user = user(username);
    LocalDateTime now = LocalDateTime.now();
    List<LiteratureReviewTask> tasks = taskRepository.findByReviewerIdOrderByClaimedAtDesc(user.getId());
    tasks.forEach(task -> {
      if (task.getStatus() == LiteratureReviewTaskStatus.ACCEPTED && task.getDueAt().isBefore(now)) {
        task.setStatus(LiteratureReviewTaskStatus.OVERDUE);
      }
      if (task.getAuthors() == null || task.getAuthors().isBlank() || task.getPublicationYear() == null) {
        JsonNode paper = literatureIntegrationService.getPaper(task.getLiteraturePaperId()).body();
        if (task.getAuthors() == null || task.getAuthors().isBlank()) task.setAuthors(limit(authors(paper.path("author")), 500));
        if (task.getPublicationYear() == null) task.setPublicationYear(publicationYear(paper));
      }
    });
    return taskRepository.saveAll(tasks).stream().map(this::toDto).toList();
  }

  @Transactional(readOnly = true)
  public LiteratureReviewerProfileDto myProfile(String username) {
    User user = user(username);
    return toProfileDto(profileRepository.findByUserId(user.getId()).orElseGet(() -> defaultProfile(user)));
  }

  @Transactional
  public void completeAcceptedTask(User user, Long paperId) {
    LiteratureReviewTask task = taskRepository.findByLiteraturePaperIdAndReviewerId(paperId, user.getId()).orElse(null);
    if (task == null || task.getStatus() == LiteratureReviewTaskStatus.COMPLETED) return;
    LocalDateTime now = LocalDateTime.now();
    int points = now.isAfter(task.getDueAt()) ? LATE_POINTS : ON_TIME_POINTS;
    task.setStatus(LiteratureReviewTaskStatus.COMPLETED);
    task.setCompletedAt(now);
    task.setAwardedPoints(points);
    taskRepository.save(task);

    LiteratureReviewerProfile profile = profile(user);
    profile.setCompletedTasks(profile.getCompletedTasks() + 1);
    if (!now.isAfter(task.getDueAt())) profile.setOnTimeTasks(profile.getOnTimeTasks() + 1);
    profile.setPoints(profile.getPoints() + points);
    refreshLevel(profile);
    profileRepository.save(profile);
  }

  private void validateDeclaration(LiteratureConflictDeclarationRequest request) {
    if (request == null || request.getAuthorOrCoauthor() == null || request.getSameInstitution() == null || request.getRecentCollaborator() == null || request.getAdvisorOrStudent() == null || request.getOtherDirectConflict() == null) {
      throw new IllegalArgumentException("Complete every conflict-of-interest declaration");
    }
    if (request.getAuthorOrCoauthor() || request.getSameInstitution() || request.getRecentCollaborator() || request.getAdvisorOrStudent() || request.getOtherDirectConflict()) {
      throw new IllegalArgumentException("A declared conflict of interest prevents this task from being claimed");
    }
  }

  private User user(String username) {
    return userRepository.findByUsername(username).orElseThrow(() -> new NotFoundException("User not found"));
  }

  private LiteratureReviewerProfile profile(User user) {
    return profileRepository.findByUserId(user.getId()).orElseGet(() -> profileRepository.save(defaultProfile(user)));
  }

  private LiteratureReviewerProfile defaultProfile(User user) {
    LiteratureReviewerProfile profile = new LiteratureReviewerProfile();
    profile.setUser(user);
    profile.setCreditScore(75);
    profile.setLevel("B");
    profile.setEligible(true);
    return profile;
  }

  private void refreshLevel(LiteratureReviewerProfile profile) {
    double credit = profile.getCreditScore();
    profile.setLevel(credit >= 85 ? "A" : credit >= 70 ? "B" : credit >= 60 ? "C" : "D");
    profile.setEligible(credit >= 60);
  }

  private LiteratureReviewTaskDto fromPaper(JsonNode paper) {
    LiteratureReviewTaskDto dto = new LiteratureReviewTaskDto();
    dto.setLiteraturePaperId(paper.path("id").asLong());
    dto.setTitle(paper.path("title").asText("Untitled literature"));
    dto.setAuthors(authors(paper.path("author")));
    dto.setJournal(paper.path("journal").asText(null));
    dto.setYear(publicationYear(paper));
    dto.setStatus("AVAILABLE");
    return dto;
  }

  private LiteratureReviewTaskDto toDto(LiteratureReviewTask task) {
    LiteratureReviewTaskDto dto = new LiteratureReviewTaskDto();
    dto.setId(task.getId()); dto.setLiteraturePaperId(task.getLiteraturePaperId()); dto.setTitle(task.getTitle());
    dto.setAuthors(task.getAuthors()); dto.setJournal(task.getJournal()); dto.setYear(task.getPublicationYear());
    dto.setStatus(task.getStatus().name()); dto.setClaimedAt(task.getClaimedAt()); dto.setDueAt(task.getDueAt());
    dto.setCompletedAt(task.getCompletedAt()); dto.setAwardedPoints(task.getAwardedPoints());
    return dto;
  }

  private LiteratureReviewerProfileDto toProfileDto(LiteratureReviewerProfile profile) {
    LiteratureReviewerProfileDto dto = new LiteratureReviewerProfileDto();
    dto.setPoints(profile.getPoints()); dto.setAcceptedTasks(profile.getAcceptedTasks()); dto.setCompletedTasks(profile.getCompletedTasks());
    dto.setOnTimeTasks(profile.getOnTimeTasks()); dto.setOnTimeRate(profile.getAcceptedTasks() == 0 ? 0 : Math.round(profile.getOnTimeTasks() * 1000.0 / profile.getAcceptedTasks()) / 10.0);
    dto.setCreditScore(profile.getCreditScore()); dto.setLevel(profile.getLevel()); dto.setEligible(profile.isEligible());
    return dto;
  }

  private String authors(JsonNode node) {
    if (node.isTextual()) return node.asText();
    if (!node.isArray()) return null;
    List<String> names = new ArrayList<>();
    node.forEach(author -> names.add(author.asText()));
    return String.join(", ", names);
  }

  private String limit(String value, int max) {
    return value == null || value.length() <= max ? value : value.substring(0, max);
  }

  private Integer publicationYear(JsonNode paper) {
    if (paper.path("year").isNumber()) return paper.path("year").asInt();
    String published = paper.path("published_date").asText("");
    if (published.matches("\\d{4}.*")) return Integer.valueOf(published.substring(0, 4));
    return null;
  }
}
