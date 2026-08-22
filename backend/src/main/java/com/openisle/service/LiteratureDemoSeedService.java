package com.openisle.service;

import com.openisle.dto.LiteratureRatingRequest;
import com.openisle.model.Role;
import com.openisle.model.User;
import com.openisle.repository.UserRepository;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

/** Development-only data builder that exercises the normal human-rating path. */
@Service
@RequiredArgsConstructor
public class LiteratureDemoSeedService {

  private static final int USER_COUNT = 12;
  private static final int RATERS_PER_PAPER = 10;
  private static final String[] DOMAINS = {
    "demo-a.edu", "demo-b.edu", "demo-c.ac.cn", "demo-d.org"
  };

  private final UserRepository userRepository;
  private final PasswordEncoder passwordEncoder;
  private final LiteratureRatingService ratingService;

  public SeedResult seed(List<Long> requestedPaperIds) {
    List<Long> paperIds = requestedPaperIds.stream().distinct().limit(5).toList();
    if (paperIds.size() < 5) {
      throw new IllegalArgumentException("Five complete literature paper IDs are required");
    }
    List<User> users = java.util.stream.IntStream
      .range(0, USER_COUNT)
      .mapToObj(this::ensureUser)
      .toList();

    int written = 0;
    for (int paperIndex = 0; paperIndex < paperIds.size(); paperIndex++) {
      for (int userIndex = 0; userIndex < RATERS_PER_PAPER; userIndex++) {
        User user = users.get(userIndex);
        ratingService.rateLiterature(
          user.getUsername(), paperIds.get(paperIndex), request(paperIndex, userIndex)
        );
        written++;
      }
    }
    return new SeedResult(users.size(), paperIds.size(), written);
  }

  private User ensureUser(int index) {
    String username = "literature_demo_reader_" + String.format("%02d", index + 1);
    return userRepository.findByUsername(username).orElseGet(() -> {
      User user = new User();
      user.setUsername(username);
      user.setEmail(username + "@" + DOMAINS[index % DOMAINS.length]);
      user.setPassword(passwordEncoder.encode("demo-rating-disabled-login"));
      user.setRole(Role.USER);
      user.setVerified(true);
      user.setApproved(true);
      user.setIntroduction("Deterministic development account for literature ranking verification.");
      return userRepository.save(user);
    });
  }

  private LiteratureRatingRequest request(int paperIndex, int userIndex) {
    LiteratureRatingRequest request = new LiteratureRatingRequest();
    request.setOriginalityScore(score(paperIndex, userIndex, 0));
    request.setRigorScore(score(paperIndex, userIndex, 1));
    request.setEvidenceScore(score(paperIndex, userIndex, 2));
    request.setSignificanceScore(score(paperIndex, userIndex, 3));
    request.setReproducibilityScore(score(paperIndex, userIndex, 4));
    request.setClarityScore(score(paperIndex, userIndex, 5));
    request.setReadConfirmed(true);
    request.setComment(
      "Deterministic demo evaluation after reviewing the paper's main content and methods."
    );
    return request;
  }

  private int score(int paperIndex, int userIndex, int dimensionIndex) {
    return 2 + Math.floorMod(17 - paperIndex + userIndex + dimensionIndex, 4);
  }

  public record SeedResult(int usersAvailable, int papersRated, int ratingsWritten) {}
}
