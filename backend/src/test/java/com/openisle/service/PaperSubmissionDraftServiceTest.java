package com.openisle.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.openisle.dto.PaperSubmissionDraftDto;
import com.openisle.model.PaperSubmissionDraft;
import com.openisle.model.PaperSubmissionDraftKind;
import com.openisle.model.PaperSubmissionDraftStatus;
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
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

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
}
