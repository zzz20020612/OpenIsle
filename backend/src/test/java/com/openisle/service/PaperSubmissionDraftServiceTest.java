package com.openisle.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.openisle.dto.PaperSubmissionDraftDto;
import com.openisle.dto.PaperSubmissionDraftRenameRequest;
import com.openisle.dto.PaperArticleDto;
import com.openisle.model.PaperArticleStatus;
import com.openisle.model.PaperFileRole;
import com.openisle.model.PaperSubmissionDraft;
import com.openisle.model.PaperSubmissionDraftKind;
import com.openisle.model.PaperSubmissionDraftStatus;
import com.openisle.model.PaperSubmissionFile;
import com.openisle.model.PaperProfile;
import com.openisle.model.PaperPublicationStatus;
import com.openisle.model.Post;
import com.openisle.model.User;
import com.openisle.repository.PaperAuthorAffiliationRepository;
import com.openisle.repository.PaperAuthorRepository;
import com.openisle.repository.PaperFileRepository;
import com.openisle.repository.PaperFundingRecordRepository;
import com.openisle.repository.PaperProfileRepository;
import com.openisle.repository.PaperSubmissionDraftRepository;
import com.openisle.repository.PaperSubmissionFileRepository;
import com.openisle.repository.UserRepository;
import java.util.List;
import java.util.Optional;
import java.time.LocalDateTime;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.access.AccessDeniedException;

@ExtendWith(MockitoExtension.class)
class PaperSubmissionDraftServiceTest {

  @Mock
  private PaperSubmissionDraftRepository draftRepository;

  @Mock
  private PaperSubmissionFileRepository fileRepository;

  @Mock
  private PaperProfileRepository paperProfileRepository;

  @Mock
  private PaperAuthorRepository paperAuthorRepository;

  @Mock
  private PaperAuthorAffiliationRepository paperAuthorAffiliationRepository;

  @Mock
  private PaperFundingRecordRepository paperFundingRecordRepository;

  @Mock
  private PaperFileRepository paperFileRepository;

  @Mock
  private UserRepository userRepository;

  @Mock
  private PaperSubmissionValidator validator;

  @Mock
  private PaperArticleService articleService;

  @Mock
  private PaperService paperService;

  @Mock
  private ObjectMapper objectMapper;

  @InjectMocks
  private PaperSubmissionDraftService service;

  @Test
  void activeOriginalDraftListOmitsBlankRowsAndRevisionDrafts() throws Exception {
    User owner = new User();
    owner.setId(42L);

    PaperSubmissionDraft meaningful = new PaperSubmissionDraft();
    meaningful.setId(101L);
    meaningful.setCreatedBy(owner);
    meaningful.setFormDataJson("{\"title\":\"Saved work\"}");

    PaperSubmissionDraft blank = new PaperSubmissionDraft();
    blank.setId(102L);
    blank.setCreatedBy(owner);
    blank.setFormDataJson("{}");
    blank.setVersion(4L);
    blank.setArticleStatus(PaperArticleStatus.IN_PROGRESS);
    blank.setArticleJson("{\"sections\":[]}");

    when(userRepository.findByUsername("user1")).thenReturn(Optional.of(owner));
    when(
      draftRepository
        .findByCreatedByIdAndStatusAndRevisionSourcePaperIsNullOrderByUpdatedAtDescIdDesc(
          42L,
          PaperSubmissionDraftStatus.IN_PROGRESS
        )
    ).thenReturn(List.of(meaningful, blank));
    when(fileRepository.findByDraftIdOrderBySortOrderAscIdAsc(101L)).thenReturn(List.of());
    when(fileRepository.findByDraftIdOrderBySortOrderAscIdAsc(102L)).thenReturn(List.of());
    when(
      objectMapper.readValue(
        "{\"title\":\"Saved work\"}",
        com.openisle.dto.PaperSubmitRequest.class
      )
    ).thenAnswer(invocation -> {
      var form = new com.openisle.dto.PaperSubmitRequest();
      form.setTitle("Saved work");
      return form;
    });
    when(objectMapper.readValue("{}", com.openisle.dto.PaperSubmitRequest.class))
      .thenReturn(new com.openisle.dto.PaperSubmitRequest());
    when(objectMapper.readValue("{\"sections\":[]}", PaperArticleDto.class))
      .thenReturn(new PaperArticleDto());

    List<PaperSubmissionDraftDto> result = service.listDrafts(
      "user1",
      PaperSubmissionDraftKind.ORIGINAL
    );

    assertEquals(1, result.size());
    assertEquals(101L, result.get(0).getId());
    assertEquals("Saved work", result.get(0).getFormData().getTitle());
  }

  @Test
  void activeRevisionDraftListKeepsPrefilledVersionZeroDraft() throws Exception {
    User owner = new User();
    owner.setId(42L);
    PaperProfile source = revisionSource(owner, 8L, "Source paper title");
    PaperSubmissionDraft revision = new PaperSubmissionDraft();
    revision.setId(103L);
    revision.setCreatedBy(owner);
    revision.setRevisionSourcePaper(source);
    revision.setFormDataJson("{}");

    when(userRepository.findByUsername("user1")).thenReturn(Optional.of(owner));
    when(
      draftRepository
        .findByCreatedByIdAndStatusAndRevisionSourcePaperIsNotNullOrderByUpdatedAtDescIdDesc(
          42L,
          PaperSubmissionDraftStatus.IN_PROGRESS
        )
    ).thenReturn(List.of(revision));
    when(fileRepository.findByDraftIdOrderBySortOrderAscIdAsc(103L)).thenReturn(List.of());
    when(objectMapper.readValue("{}", com.openisle.dto.PaperSubmitRequest.class))
      .thenReturn(new com.openisle.dto.PaperSubmitRequest());

    List<PaperSubmissionDraftDto> result = service.listDrafts(
      "user1",
      PaperSubmissionDraftKind.REVISION
    );

    assertEquals(1, result.size());
    assertEquals(103L, result.get(0).getId());
    assertEquals(8L, result.get(0).getRevisionSourcePaperId());
  }

  @Test
  void currentOriginalDraftDoesNotResumeLatestRevisionDraft() throws Exception {
    User owner = new User();
    owner.setId(42L);
    PaperSubmissionDraft original = new PaperSubmissionDraft();
    original.setId(101L);
    original.setCreatedBy(owner);
    original.setFormDataJson("{}");

    when(userRepository.findByUsername("user1")).thenReturn(Optional.of(owner));
    when(
      draftRepository
        .findFirstByCreatedByIdAndStatusAndRevisionSourcePaperIsNullOrderByUpdatedAtDescIdDesc(
          42L,
          PaperSubmissionDraftStatus.IN_PROGRESS
        )
    ).thenReturn(Optional.of(original));
    when(fileRepository.findByDraftIdOrderBySortOrderAscIdAsc(101L)).thenReturn(List.of());
    when(objectMapper.readValue("{}", com.openisle.dto.PaperSubmitRequest.class))
      .thenReturn(new com.openisle.dto.PaperSubmitRequest());

    Optional<PaperSubmissionDraftDto> result = service.getCurrentDraft(
      "user1",
      PaperSubmissionDraftKind.ORIGINAL
    );

    assertTrue(result.isPresent());
    assertEquals(101L, result.orElseThrow().getId());
    verify(
      draftRepository,
      never()
    ).findFirstByCreatedByIdAndStatusOrderByUpdatedAtDescIdDesc(
      42L,
      PaperSubmissionDraftStatus.IN_PROGRESS
    );
  }

  @Test
  void revisionDraftIsCreatedFromTheRequestedPaperInsteadOfBlank() throws Exception {
    User owner = new User();
    owner.setId(42L);
    PaperProfile source = revisionSource(owner, 8L, "Source paper title");

    when(userRepository.findByUsername("user1")).thenReturn(Optional.of(owner));
    when(paperProfileRepository.findById(8L)).thenReturn(Optional.of(source));
    when(
      draftRepository.findFirstByRevisionSourcePaperIdAndStatusOrderByUpdatedAtDescIdDesc(
        8L,
        PaperSubmissionDraftStatus.IN_PROGRESS
      )
    ).thenReturn(Optional.empty());
    when(paperAuthorRepository.findByPaperIdOrderByAuthorOrderAsc(8L)).thenReturn(List.of());
    when(paperFundingRecordRepository.findByPaperIdOrderByDisplayOrderAscIdAsc(8L)).thenReturn(List.of());
    when(paperFileRepository.findByPaperIdOrderBySortOrderAscIdAsc(8L)).thenReturn(List.of());
    when(fileRepository.saveAllAndFlush(any())).thenReturn(List.of());
    when(fileRepository.findByDraftIdOrderBySortOrderAscIdAsc(301L)).thenReturn(List.of());
    when(objectMapper.writeValueAsString(any(com.openisle.dto.PaperSubmitRequest.class)))
      .thenReturn("{\"title\":\"Source paper title\"}");
    when(objectMapper.readValue("{\"title\":\"Source paper title\"}", com.openisle.dto.PaperSubmitRequest.class))
      .thenAnswer(invocation -> {
        var form = new com.openisle.dto.PaperSubmitRequest();
        form.setTitle("Source paper title");
        return form;
      });
    when(draftRepository.saveAndFlush(any(PaperSubmissionDraft.class))).thenAnswer(invocation -> {
      PaperSubmissionDraft draft = invocation.getArgument(0);
      if (draft.getId() == null) draft.setId(301L);
      return draft;
    });

    PaperSubmissionDraftDto result = service.createRevisionDraft("user1", 8L);

    assertEquals(301L, result.getId());
    assertEquals(8L, result.getRevisionSourcePaperId());
    assertEquals("Source paper title", result.getRevisionSourcePaperTitle());
    assertEquals("Source paper title", result.getFormData().getTitle());
    assertEquals(PaperSubmissionDraftStatus.IN_PROGRESS, result.getStatus());
    assertFalse(result.getFiles().iterator().hasNext());
  }

  @Test
  void revisionDraftResumesOnlyTheInProgressDraftForThatPaper() throws Exception {
    User owner = new User();
    owner.setId(42L);
    PaperProfile source = revisionSource(owner, 8L, "Source paper title");
    PaperSubmissionDraft existing = new PaperSubmissionDraft();
    existing.setId(302L);
    existing.setCreatedBy(owner);
    existing.setRevisionSourcePaper(source);
    existing.setStatus(PaperSubmissionDraftStatus.IN_PROGRESS);
    existing.setFormDataJson("{}");

    when(userRepository.findByUsername("user1")).thenReturn(Optional.of(owner));
    when(paperProfileRepository.findById(8L)).thenReturn(Optional.of(source));
    when(
      draftRepository.findFirstByRevisionSourcePaperIdAndStatusOrderByUpdatedAtDescIdDesc(
        8L,
        PaperSubmissionDraftStatus.IN_PROGRESS
      )
    ).thenReturn(Optional.of(existing));
    when(fileRepository.findByDraftIdOrderBySortOrderAscIdAsc(302L)).thenReturn(List.of());
    when(objectMapper.readValue("{}", com.openisle.dto.PaperSubmitRequest.class))
      .thenReturn(new com.openisle.dto.PaperSubmitRequest());

    PaperSubmissionDraftDto result = service.createRevisionDraft("user1", 8L);

    assertEquals(302L, result.getId());
    assertEquals(8L, result.getRevisionSourcePaperId());
    verify(draftRepository, never()).saveAndFlush(any(PaperSubmissionDraft.class));
  }

  @Test
  void revisionDraftIsNotCreatedAfterANewerRevisionWasSubmitted() {
    User owner = new User();
    owner.setId(42L);
    PaperProfile source = revisionSource(owner, 8L, "Source paper title");
    PaperProfile submittedRevision = revisionSource(owner, 11L, "Submitted revision");

    when(userRepository.findByUsername("user1")).thenReturn(Optional.of(owner));
    when(paperProfileRepository.findById(8L)).thenReturn(Optional.of(source));
    when(paperProfileRepository.findFirstByRevisionOfPaperIdOrderByRevisionNumberDescIdDesc(8L))
      .thenReturn(Optional.of(submittedRevision));

    assertThrows(
      IllegalStateException.class,
      () -> service.createRevisionDraft("user1", 8L)
    );
    verify(draftRepository, never())
      .findFirstByRevisionSourcePaperIdAndStatusOrderByUpdatedAtDescIdDesc(
        8L,
        PaperSubmissionDraftStatus.IN_PROGRESS
      );
  }

  @Test
  void renameDraftTrimsTheNameAndBlankClearsIt() throws Exception {
    User owner = new User();
    owner.setId(42L);
    PaperSubmissionDraft draft = new PaperSubmissionDraft();
    draft.setId(104L);
    draft.setCreatedBy(owner);
    draft.setFormDataJson("{}");

    when(userRepository.findByUsername("user1")).thenReturn(Optional.of(owner));
    when(draftRepository.findById(104L)).thenReturn(Optional.of(draft));
    when(draftRepository.saveAndFlush(draft)).thenReturn(draft);
    when(fileRepository.findByDraftIdOrderBySortOrderAscIdAsc(104L)).thenReturn(List.of());
    when(objectMapper.readValue("{}", com.openisle.dto.PaperSubmitRequest.class))
      .thenReturn(new com.openisle.dto.PaperSubmitRequest());

    PaperSubmissionDraftRenameRequest named = new PaperSubmissionDraftRenameRequest();
    named.setDisplayName("  Lake pollution manuscript  ");
    PaperSubmissionDraftDto renamed = service.renameDraft("user1", 104L, named);
    assertEquals("Lake pollution manuscript", renamed.getDisplayName());

    PaperSubmissionDraftRenameRequest cleared = new PaperSubmissionDraftRenameRequest();
    cleared.setDisplayName("   ");
    PaperSubmissionDraftDto result = service.renameDraft("user1", 104L, cleared);
    assertEquals(null, result.getDisplayName());
  }

  @Test
  void draftDtoIncludesFileSummaryAndStaleMarker() throws Exception {
    User owner = new User();
    owner.setId(42L);
    PaperSubmissionDraft draft = new PaperSubmissionDraft();
    draft.setId(105L);
    draft.setCreatedBy(owner);
    draft.setFormDataJson("{\"title\":\"Parsed manuscript\"}");
    draft.setUpdatedAt(LocalDateTime.now().minusDays(31));

    PaperSubmissionFile manuscript = new PaperSubmissionFile();
    manuscript.setId(501L);
    manuscript.setRole(PaperFileRole.MANUSCRIPT);
    manuscript.setOriginalFileName("pollution-study.docx");

    when(userRepository.findByUsername("user1")).thenReturn(Optional.of(owner));
    when(draftRepository.findById(105L)).thenReturn(Optional.of(draft));
    when(fileRepository.findByDraftIdOrderBySortOrderAscIdAsc(105L))
      .thenReturn(List.of(manuscript));
    when(objectMapper.readValue(
      "{\"title\":\"Parsed manuscript\"}",
      com.openisle.dto.PaperSubmitRequest.class
    )).thenAnswer(invocation -> {
      var form = new com.openisle.dto.PaperSubmitRequest();
      form.setTitle("Parsed manuscript");
      return form;
    });

    PaperSubmissionDraftDto result = service.getDraft("user1", 105L);

    assertEquals("Parsed manuscript", result.getManuscriptTitle());
    assertEquals("pollution-study.docx", result.getPrimaryManuscriptFileName());
    assertEquals(1, result.getFileCount());
    assertTrue(result.isStale());
  }

  @Test
  void renameDraftRejectsAnotherUsersDraft() {
    User owner = new User();
    owner.setId(42L);
    User anotherUser = new User();
    anotherUser.setId(99L);
    PaperSubmissionDraft draft = new PaperSubmissionDraft();
    draft.setId(106L);
    draft.setCreatedBy(owner);

    when(userRepository.findByUsername("user2")).thenReturn(Optional.of(anotherUser));
    when(draftRepository.findById(106L)).thenReturn(Optional.of(draft));

    assertThrows(
      AccessDeniedException.class,
      () -> service.renameDraft("user2", 106L, new PaperSubmissionDraftRenameRequest())
    );
    verify(draftRepository, never()).saveAndFlush(any(PaperSubmissionDraft.class));
  }

  @Test
  void renameDraftRejectsSubmittedDraft() {
    User owner = new User();
    owner.setId(42L);
    PaperSubmissionDraft draft = new PaperSubmissionDraft();
    draft.setId(107L);
    draft.setCreatedBy(owner);
    draft.setStatus(PaperSubmissionDraftStatus.SUBMITTED);

    when(userRepository.findByUsername("user1")).thenReturn(Optional.of(owner));
    when(draftRepository.findById(107L)).thenReturn(Optional.of(draft));

    assertThrows(
      IllegalStateException.class,
      () -> service.renameDraft("user1", 107L, new PaperSubmissionDraftRenameRequest())
    );
    verify(draftRepository, never()).saveAndFlush(any(PaperSubmissionDraft.class));
  }

  private static PaperProfile revisionSource(User owner, Long id, String title) {
    Post post = new Post();
    post.setContent("Source content");
    PaperProfile source = new PaperProfile();
    source.setId(id);
    source.setCreatedBy(owner);
    source.setPost(post);
    source.setTitle(title);
    source.setAbstractText("Source abstract");
    source.setSubjectArea("Computer Science");
    source.setPaperType("Research Article");
    source.setPublicationStatus(PaperPublicationStatus.NEEDS_REVISION);
    return source;
  }
}
