package com.openisle.service;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.openisle.dto.LiteratureConflictDeclarationRequest;
import com.openisle.dto.LiteratureReviewTaskDto;
import com.openisle.model.LiteratureReviewTask;
import com.openisle.model.LiteratureReviewTaskStatus;
import com.openisle.model.LiteratureReviewerProfile;
import com.openisle.model.User;
import com.openisle.repository.*;
import com.openisle.service.LiteratureIntegrationService.LiteratureProxyResponse;
import java.time.LocalDateTime;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

class LiteratureReviewTaskServiceTest {
  private final LiteratureReviewTaskRepository tasks = mock(LiteratureReviewTaskRepository.class);
  private final LiteratureReviewerProfileRepository profiles = mock(LiteratureReviewerProfileRepository.class);
  private final LiteratureRatingRepository ratings = mock(LiteratureRatingRepository.class);
  private final UserRepository users = mock(UserRepository.class);
  private final LiteratureIntegrationService literature = mock(LiteratureIntegrationService.class);
  private final LiteratureReviewTaskService service = new LiteratureReviewTaskService(tasks, profiles, ratings, users, literature);
  private final User user = new User();

  @BeforeEach
  void setup() {
    user.setId(1L); user.setUsername("user1"); user.setEmail("user1@example.edu");
    when(users.findByUsername("user1")).thenReturn(Optional.of(user));
    when(profiles.findByUserId(1L)).thenReturn(Optional.empty());
    when(profiles.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
  }

  @Test
  void cleanDeclarationClaimsCompletePaperAndIncrementsAcceptedCount() {
    when(tasks.findByLiteraturePaperIdAndReviewerId(4L, 1L)).thenReturn(Optional.empty());
    when(literature.getPaper(4L)).thenReturn(new LiteratureProxyResponse(HttpStatus.OK, completePaper()));
    when(tasks.save(any())).thenAnswer(invocation -> { LiteratureReviewTask task = invocation.getArgument(0); task.setId(8L); return task; });

    LiteratureReviewTaskDto result = service.claim("user1", 4L, cleanDeclaration());

    assertEquals("ACCEPTED", result.getStatus());
    assertEquals(4L, result.getLiteraturePaperId());
    assertNotNull(result.getDueAt());
    verify(profiles, atLeastOnce()).save(argThat(profile -> profile.getAcceptedTasks() == 1));
  }

  @Test
  void declaredConflictBlocksClaimWithoutWritingTask() {
    LiteratureConflictDeclarationRequest request = cleanDeclaration();
    request.setSameInstitution(true);

    IllegalArgumentException error = assertThrows(IllegalArgumentException.class, () -> service.claim("user1", 4L, request));

    assertTrue(error.getMessage().contains("conflict"));
    verify(tasks, never()).save(any());
  }

  @Test
  void ratingCompletionAwardsPointsExactlyOnce() {
    LiteratureReviewTask task = new LiteratureReviewTask();
    task.setLiteraturePaperId(4L); task.setReviewer(user); task.setStatus(LiteratureReviewTaskStatus.ACCEPTED);
    task.setDueAt(LocalDateTime.now().plusDays(1));
    AtomicReference<LiteratureReviewerProfile> savedProfile = new AtomicReference<>();
    when(tasks.findByLiteraturePaperIdAndReviewerId(4L, 1L)).thenReturn(Optional.of(task));
    when(profiles.save(any())).thenAnswer(invocation -> { savedProfile.set(invocation.getArgument(0)); return savedProfile.get(); });

    service.completeAcceptedTask(user, 4L);
    service.completeAcceptedTask(user, 4L);

    assertEquals(LiteratureReviewTaskStatus.COMPLETED, task.getStatus());
    assertEquals(20, task.getAwardedPoints());
    assertEquals(20, savedProfile.get().getPoints());
    assertEquals(1, savedProfile.get().getCompletedTasks());
  }

  private ObjectNode completePaper() {
    ObjectNode paper = JsonNodeFactory.instance.objectNode();
    paper.put("id", 4); paper.put("title", "Complete paper"); paper.put("journal", "Journal"); paper.put("year", 2026);
    paper.putObject("completeness").put("state", "complete");
    paper.putArray("author").add("Author One");
    return paper;
  }

  private LiteratureConflictDeclarationRequest cleanDeclaration() {
    LiteratureConflictDeclarationRequest request = new LiteratureConflictDeclarationRequest();
    request.setAuthorOrCoauthor(false); request.setSameInstitution(false); request.setRecentCollaborator(false);
    request.setAdvisorOrStudent(false); request.setOtherDirectConflict(false);
    return request;
  }
}
