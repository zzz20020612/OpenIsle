package com.openisle.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.mockito.Mockito.lenient;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.openisle.dto.PaperArticleBlockDto;
import com.openisle.dto.PaperArticleDto;
import com.openisle.dto.PaperArticleSectionDto;
import com.openisle.dto.PaperArticleValidationDto;
import com.openisle.exception.DraftVersionConflictException;
import com.openisle.model.PaperArticleStatus;
import com.openisle.model.PaperFile;
import com.openisle.model.PaperFileRole;
import com.openisle.model.PaperSubmissionDraft;
import com.openisle.model.PaperSubmissionDraftStatus;
import com.openisle.model.PaperSubmissionFile;
import com.openisle.model.User;
import com.openisle.model.PaperProfile;
import com.openisle.repository.PaperFileRepository;
import com.openisle.repository.PaperProfileRepository;
import com.openisle.repository.PaperSubmissionDraftRepository;
import com.openisle.repository.PaperSubmissionFileRepository;
import com.openisle.repository.UserRepository;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.access.AccessDeniedException;

@ExtendWith(MockitoExtension.class)
class PaperArticleServiceTest {

  @Mock private PaperSubmissionDraftRepository draftRepository;
  @Mock private PaperSubmissionFileRepository fileRepository;
  @Mock private PaperProfileRepository paperProfileRepository;
  @Mock private PaperFileRepository paperFileRepository;
  @Mock private UserRepository userRepository;
  @Mock private PaperArticleValidator validator;
  @Mock private PaperAccessPolicy paperAccessPolicy;

  private PaperArticleService service;
  private User owner;
  private PaperSubmissionDraft draft;

  @BeforeEach
  void setUp() {
    service = new PaperArticleService(
      draftRepository,
      fileRepository,
      paperProfileRepository,
      paperFileRepository,
      userRepository,
      validator,
      paperAccessPolicy,
      new ObjectMapper().findAndRegisterModules()
    );
    owner = new User();
    owner.setId(7L);
    owner.setUsername("owner");
    draft = new PaperSubmissionDraft();
    draft.setId(11L);
    draft.setCreatedBy(owner);
    draft.setStatus(PaperSubmissionDraftStatus.IN_PROGRESS);
    draft.setArticleStatus(PaperArticleStatus.NOT_STARTED);
    lenient().when(userRepository.findByUsername("owner")).thenReturn(Optional.of(owner));
    lenient().when(draftRepository.findById(11L)).thenReturn(Optional.of(draft));
  }

  @Test
  void rejectsArticleAccessFromAnotherUser() {
    User other = new User();
    other.setId(8L);
    other.setUsername("other");
    when(userRepository.findByUsername("other")).thenReturn(Optional.of(other));

    assertThrows(AccessDeniedException.class, () -> service.getDraftArticle("other", 11L));
  }

  @Test
  void rejectsStaleArticleVersion() {
    draft.setArticleVersion(4L);
    PaperArticleDto request = article(3L);

    assertThrows(
      DraftVersionConflictException.class,
      () -> service.updateDraftArticle("owner", 11L, request)
    );
  }

  @Test
  void savesArticleAndMarksItInProgress() {
    PaperArticleDto saved = service.updateDraftArticle("owner", 11L, article(0L));

    assertEquals(1L, saved.getVersion());
    assertEquals(PaperArticleStatus.IN_PROGRESS, saved.getStatus());
    verify(draftRepository).saveAndFlush(draft);
  }

  @Test
  void marksValidArticleReady() {
    PaperArticleValidationDto validation = new PaperArticleValidationDto();
    validation.setValid(true);
    when(fileRepository.findByDraftIdOrderBySortOrderAscIdAsc(11L)).thenReturn(List.of());
    when(validator.validate(any(PaperArticleDto.class), any())).thenReturn(validation);

    PaperArticleDto ready = service.markReady("owner", 11L, article(0L));

    assertEquals(1L, ready.getVersion());
    assertEquals(PaperArticleStatus.READY, ready.getStatus());
    verify(draftRepository).saveAndFlush(draft);
  }

  @Test
  void remapsDraftFigureIdsWhenCopyingArticleToPublishedPaper() throws Exception {
    draft.setArticleStatus(PaperArticleStatus.READY);
    PaperArticleDto article = article(1L);
    PaperArticleBlockDto figure = new PaperArticleBlockDto();
    figure.setKey("figure-1");
    figure.setType("FIGURE");
    figure.setFileId(9L);
    article.getSections().get(0).setBlocks(List.of(figure));
    draft.setArticleJson(new ObjectMapper().writeValueAsString(article));

    PaperSubmissionFile source = new PaperSubmissionFile();
    source.setId(9L);
    source.setRole(PaperFileRole.FIGURE);
    source.setStorageKey("figures/one.jpg");
    PaperFile published = new PaperFile();
    published.setId(105L);
    published.setRole(PaperFileRole.FIGURE);
    published.setStorageKey("figures/one.jpg");
    PaperProfile paper = new PaperProfile();
    paper.setId(5L);

    when(fileRepository.findByDraftIdOrderBySortOrderAscIdAsc(11L)).thenReturn(List.of(source));
    when(paperFileRepository.findByPaperIdOrderBySortOrderAscIdAsc(5L)).thenReturn(List.of(published));
    PaperArticleValidationDto validation = new PaperArticleValidationDto();
    validation.setValid(true);
    when(validator.validate(any(PaperArticleDto.class), any())).thenReturn(validation);

    service.copyToPaper(draft, paper);

    PaperArticleDto saved = new ObjectMapper().readValue(paper.getArticleJson(), PaperArticleDto.class);
    assertEquals(105L, saved.getSections().get(0).getBlocks().get(0).getFileId());
  }

  private PaperArticleDto article(long version) {
    PaperArticleDto article = new PaperArticleDto();
    article.setVersion(version);
    PaperArticleSectionDto section = new PaperArticleSectionDto();
    section.setKey("introduction");
    section.setHeading("Introduction");
    PaperArticleBlockDto paragraph = new PaperArticleBlockDto();
    paragraph.setKey("paragraph-1");
    paragraph.setType("PARAGRAPH");
    paragraph.setText("Structured text");
    section.setBlocks(List.of(paragraph));
    article.setSections(List.of(section));
    return article;
  }
}
