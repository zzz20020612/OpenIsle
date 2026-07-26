package com.openisle.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openisle.dto.PaperAuthorRequest;
import com.openisle.dto.PaperDetailDto;
import com.openisle.dto.PaperFileRecordDto;
import com.openisle.dto.PaperSubmitRequest;
import com.openisle.exception.NotFoundException;
import com.openisle.model.AiScreeningResult;
import com.openisle.model.Category;
import com.openisle.model.ExpertIdentityStatus;
import com.openisle.model.ExpertProfile;
import com.openisle.model.Institution;
import com.openisle.model.PaperAuthor;
import com.openisle.model.PaperProfile;
import com.openisle.model.PaperPublicationStatus;
import com.openisle.model.PaperScoreSnapshot;
import com.openisle.model.PaperScreeningStatus;
import com.openisle.model.Post;
import com.openisle.model.PostType;
import com.openisle.model.Tag;
import com.openisle.model.User;
import com.openisle.repository.AiScreeningResultRepository;
import com.openisle.repository.CategoryRepository;
import com.openisle.repository.ExpertProfileRepository;
import com.openisle.repository.InstitutionRepository;
import com.openisle.repository.PaperAuthorAffiliationRepository;
import com.openisle.repository.PaperAuthorRepository;
import com.openisle.repository.PaperFileRepository;
import com.openisle.repository.PaperFundingRecordRepository;
import com.openisle.repository.PaperProfileRepository;
import com.openisle.repository.PaperScoreSnapshotRepository;
import com.openisle.repository.TagRepository;
import com.openisle.repository.UserRepository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicReference;
import org.springframework.data.domain.PageRequest;
import org.mockito.ArgumentCaptor;
import org.junit.jupiter.api.Test;

class PaperServiceTest {

  @Test
  void listPublishedPapersAppliesSubjectScoreAndSortFilters() {
    PostService postService = mock(PostService.class);
    PaperProfileRepository paperProfileRepository = mock(PaperProfileRepository.class);
    PaperAuthorRepository paperAuthorRepository = mock(PaperAuthorRepository.class);
    InstitutionRepository institutionRepository = mock(InstitutionRepository.class);
    AiScreeningResultRepository aiScreeningResultRepository = mock(
      AiScreeningResultRepository.class
    );
    AiScreeningService aiScreeningService = mock(AiScreeningService.class);
    PaperScoreSnapshotRepository paperScoreSnapshotRepository = mock(
      PaperScoreSnapshotRepository.class
    );
    CategoryRepository categoryRepository = mock(CategoryRepository.class);
    TagRepository tagRepository = mock(TagRepository.class);
    UserRepository userRepository = mock(UserRepository.class);
    ExpertProfileRepository expertProfileRepository = mock(ExpertProfileRepository.class);

    PaperService service = new PaperService(
      postService,
      paperProfileRepository,
      paperAuthorRepository,
      mock(PaperAuthorAffiliationRepository.class),
      mock(PaperFundingRecordRepository.class),
      mock(PaperFileRepository.class),
      institutionRepository,
      aiScreeningResultRepository,
      aiScreeningService,
      paperScoreSnapshotRepository,
      categoryRepository,
      tagRepository,
      new PaperAccessPolicy(paperAuthorRepository),
      userRepository,
      expertProfileRepository,
      mock(SubscriptionService.class)
    );

    PaperProfile infoSystemsPaper = buildPublishedPaper(11L, 101L, "Paper A", "Information Systems", 4.6, 12);
    PaperProfile econPaper = buildPublishedPaper(12L, 102L, "Paper B", "Economics", 3.2, 8);
    PaperProfile secondInfoSystemsPaper = buildPublishedPaper(13L, 103L, "Paper C", "Information Systems", 4.1, 3);

    when(paperProfileRepository.findPublishedOrderByScoreDesc(eq("Information Systems"), eq(4.2), any())).thenReturn(
      List.of(infoSystemsPaper)
    );
    when(paperProfileRepository.findPublishedOrderByScoreDesc(isNull(), isNull(), any())).thenReturn(
      List.of(infoSystemsPaper, secondInfoSystemsPaper, econPaper)
    );
    when(paperProfileRepository.findByPublicationStatusOrderByPublishedAtDesc(any(), any())).thenReturn(
      List.of(infoSystemsPaper, econPaper, secondInfoSystemsPaper)
    );
    when(paperProfileRepository.findByPublicationStatusAndSubjectAreaIgnoreCaseOrderByPublishedAtDesc(any(), any(), any())).thenReturn(
      List.of(infoSystemsPaper, secondInfoSystemsPaper)
    );
    when(paperAuthorRepository.findByPaperIdOrderByAuthorOrderAsc(any())).thenReturn(List.of());
    when(paperScoreSnapshotRepository.findByPaperId(11L)).thenReturn(Optional.of(buildSnapshot(11L, 4.6, 12)));
    when(paperScoreSnapshotRepository.findByPaperId(12L)).thenReturn(Optional.of(buildSnapshot(12L, 3.2, 8)));
    when(paperScoreSnapshotRepository.findByPaperId(13L)).thenReturn(Optional.of(buildSnapshot(13L, 4.1, 3)));

    var filtered = service.listPublishedPapers(0, 20, "Information Systems", 4.2, "score");

    assertEquals(1, filtered.size());
    assertEquals("Paper A", filtered.get(0).getTitle());

    var sortedByScore = service.listPublishedPapers(0, 20, null, null, "score");
    assertEquals(
      List.of("Paper A", "Paper C", "Paper B"),
      sortedByScore.stream().map(item -> item.getTitle()).toList()
    );
  }

  @Test
  void listPublishedPapersUsesDatabaseQueryForScorePagination() {
    PostService postService = mock(PostService.class);
    PaperProfileRepository paperProfileRepository = mock(PaperProfileRepository.class);
    PaperAuthorRepository paperAuthorRepository = mock(PaperAuthorRepository.class);
    PaperScoreSnapshotRepository paperScoreSnapshotRepository = mock(
      PaperScoreSnapshotRepository.class
    );
    PaperService service = new PaperService(
      postService,
      paperProfileRepository,
      paperAuthorRepository,
      mock(PaperAuthorAffiliationRepository.class),
      mock(PaperFundingRecordRepository.class),
      mock(PaperFileRepository.class),
      mock(InstitutionRepository.class),
      mock(AiScreeningResultRepository.class),
      mock(AiScreeningService.class),
      paperScoreSnapshotRepository,
      mock(CategoryRepository.class),
      mock(TagRepository.class),
      new PaperAccessPolicy(paperAuthorRepository),
      mock(UserRepository.class),
      mock(ExpertProfileRepository.class),
      mock(SubscriptionService.class)
    );

    PaperProfile highScoreOlderPaper = buildPublishedPaper(31L, 301L, "High Score Older Paper", "AI", 4.9, 5);
    when(paperProfileRepository.findPublishedOrderByScoreDesc(any(), any(), any())).thenReturn(
      List.of(highScoreOlderPaper)
    );
    when(paperAuthorRepository.findByPaperIdOrderByAuthorOrderAsc(any())).thenReturn(List.of());
    when(paperScoreSnapshotRepository.findByPaperId(31L)).thenReturn(Optional.of(buildSnapshot(31L, 4.9, 5)));

    var result = service.listPublishedPapers(0, 1, null, 4.5, "score");

    assertEquals(List.of("High Score Older Paper"), result.stream().map(item -> item.getTitle()).toList());
    verify(paperProfileRepository).findPublishedOrderByScoreDesc(null, 4.5, PageRequest.of(0, 1));
  }

  @Test
  void listPublishedPapersSurfacesFeaturedPapersFirstAndExposesLinkedPostDistributionState() {
    PostService postService = mock(PostService.class);
    PaperProfileRepository paperProfileRepository = mock(PaperProfileRepository.class);
    PaperAuthorRepository paperAuthorRepository = mock(PaperAuthorRepository.class);
    PaperScoreSnapshotRepository paperScoreSnapshotRepository = mock(
      PaperScoreSnapshotRepository.class
    );
    PaperService service = new PaperService(
      postService,
      paperProfileRepository,
      paperAuthorRepository,
      mock(PaperAuthorAffiliationRepository.class),
      mock(PaperFundingRecordRepository.class),
      mock(PaperFileRepository.class),
      mock(InstitutionRepository.class),
      mock(AiScreeningResultRepository.class),
      mock(AiScreeningService.class),
      paperScoreSnapshotRepository,
      mock(CategoryRepository.class),
      mock(TagRepository.class),
      new PaperAccessPolicy(paperAuthorRepository),
      mock(UserRepository.class),
      mock(ExpertProfileRepository.class),
      mock(SubscriptionService.class)
    );

    PaperProfile latestStandard = buildPublishedPaper(21L, 201L, "Latest Standard", "AI", 3.5, 1);
    PaperProfile olderFeatured = buildPublishedPaper(22L, 202L, "Older Featured", "AI", 3.2, 2);
    olderFeatured.getPost().setPinnedAt(LocalDateTime.now().minusDays(1));
    olderFeatured.getPost().setRssExcluded(false);

    when(paperProfileRepository.findByPublicationStatusOrderByPublishedAtDesc(any(), any())).thenReturn(
      List.of(latestStandard, olderFeatured)
    );
    when(paperAuthorRepository.findByPaperIdOrderByAuthorOrderAsc(any())).thenReturn(List.of());
    when(paperScoreSnapshotRepository.findByPaperId(21L)).thenReturn(Optional.of(buildSnapshot(21L, 3.5, 1)));
    when(paperScoreSnapshotRepository.findByPaperId(22L)).thenReturn(Optional.of(buildSnapshot(22L, 3.2, 2)));

    var result = service.listPublishedPapers(0, 20, null, null, "latest");

    assertEquals(List.of("Older Featured", "Latest Standard"), result.stream().map(item -> item.getTitle()).toList());
    assertEquals(true, result.get(0).isFeatured());
    assertEquals(false, result.get(0).isRssExcluded());
  }

  @Test
  void submitPaperStartsAsynchronousScreening() {
    PostService postService = mock(PostService.class);
    PaperProfileRepository paperProfileRepository = mock(PaperProfileRepository.class);
    PaperAuthorRepository paperAuthorRepository = mock(PaperAuthorRepository.class);
    InstitutionRepository institutionRepository = mock(InstitutionRepository.class);
    AiScreeningResultRepository aiScreeningResultRepository = mock(
      AiScreeningResultRepository.class
    );
    AiScreeningService aiScreeningService = mock(AiScreeningService.class);
    PaperScoreSnapshotRepository paperScoreSnapshotRepository = mock(
      PaperScoreSnapshotRepository.class
    );
    CategoryRepository categoryRepository = mock(CategoryRepository.class);
    TagRepository tagRepository = mock(TagRepository.class);
    UserRepository userRepository = mock(UserRepository.class);
    ExpertProfileRepository expertProfileRepository = mock(ExpertProfileRepository.class);

    PaperService service = new PaperService(
      postService,
      paperProfileRepository,
      paperAuthorRepository,
      mock(PaperAuthorAffiliationRepository.class),
      mock(PaperFundingRecordRepository.class),
      mock(PaperFileRepository.class),
      institutionRepository,
      aiScreeningResultRepository,
      aiScreeningService,
      paperScoreSnapshotRepository,
      categoryRepository,
      tagRepository,
      new PaperAccessPolicy(paperAuthorRepository),
      userRepository,
      expertProfileRepository,
      mock(SubscriptionService.class)
    );

    User author = new User();
    author.setId(1L);
    author.setUsername("admin");

    User linkedAuthor = new User();
    linkedAuthor.setId(2L);
    linkedAuthor.setUsername("alice");
    linkedAuthor.setEmail("alice@example.edu");

    Post post = new Post();
    post.setId(10L);
    post.setTitle("A Test Paper for MVP Workflow");
    post.setContent("Full paper text for the MVP workflow test.");
    post.setAuthor(author);

    when(postService.createPost(
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any()
    )).thenReturn(post);

    when(categoryRepository.findByName("Papers")).thenReturn(Optional.empty());
    when(categoryRepository.save(any(Category.class))).thenAnswer(invocation -> {
      Category category = invocation.getArgument(0);
      category.setId(100L);
      return category;
    });

    when(tagRepository.findByName("Research Paper")).thenReturn(Optional.empty());
    when(tagRepository.save(any(Tag.class))).thenAnswer(invocation -> {
      Tag tag = invocation.getArgument(0);
      tag.setId(200L);
      return tag;
    });

    when(institutionRepository.findByNameIgnoreCase("Example University")).thenReturn(
      Optional.empty()
    );
    when(institutionRepository.save(any(Institution.class))).thenAnswer(invocation -> {
      Institution institution = invocation.getArgument(0);
      institution.setId(30L);
      return institution;
    });
    when(userRepository.findByEmail("alice@example.edu")).thenReturn(Optional.of(linkedAuthor));
    when(expertProfileRepository.findByOrcid("0000-0002-1825-0097")).thenReturn(Optional.empty());
    when(expertProfileRepository.findByEmailIgnoreCase("alice@example.edu")).thenReturn(Optional.empty());
    when(expertProfileRepository.save(any(ExpertProfile.class))).thenAnswer(invocation -> {
      ExpertProfile expert = invocation.getArgument(0);
      expert.setId(300L);
      return expert;
    });

    AtomicReference<List<PaperAuthor>> savedAuthors = new AtomicReference<>(List.of());
    when(paperAuthorRepository.saveAll(any())).thenAnswer(invocation -> {
      List<PaperAuthor> authors = invocation.getArgument(0);
      savedAuthors.set(authors);
      return authors;
    });
    when(paperAuthorRepository.findByPaperIdOrderByAuthorOrderAsc(20L)).thenAnswer(invocation ->
      savedAuthors.get()
    );

    when(paperProfileRepository.save(any(PaperProfile.class))).thenAnswer(invocation -> {
      PaperProfile paper = invocation.getArgument(0);
      if (paper.getId() == null) {
        paper.setId(20L);
      }
      return paper;
    });

    when(aiScreeningResultRepository.save(any(AiScreeningResult.class))).thenAnswer(invocation -> {
      AiScreeningResult result = invocation.getArgument(0);
      result.setId(40L);
      result.setScreenedAt(LocalDateTime.now());
      return result;
    });

    PaperDetailDto result = service.submitPaper("admin", buildRequest());

    assertNotNull(result.getId());
    assertEquals(10L, result.getPostId());
    assertEquals(PaperPublicationStatus.SCREENING, result.getPublicationStatus());
    assertEquals(PaperScreeningStatus.SCREENING, result.getScreeningStatus());
    assertEquals(null, result.getScreening());
    verify(aiScreeningService).requestScreening(any(PaperProfile.class));
    assertEquals(1, result.getAuthors().size());
    assertEquals(1, result.getAuthors().get(0).getAuthorOrder());
    assertEquals("Alice Researcher", result.getAuthors().get(0).getDisplayName());
    assertEquals(30L, result.getAuthors().get(0).getInstitutionId());
    assertEquals("Example University", result.getAuthors().get(0).getInstitution());
    assertEquals("United States", result.getAuthors().get(0).getCountry());
    assertEquals(true, result.getAuthors().get(0).isCorrespondingAuthor());
    assertEquals(false, result.getAuthors().get(0).isEqualContribution());
    assertEquals(ExpertIdentityStatus.ORCID_MATCHED, result.getAuthors().get(0).getIdentityStatus());
    assertEquals(300L, result.getAuthors().get(0).getExpertProfileId());
    assertEquals(List.of("paper", "mvp", "test"), result.getKeywords());
    assertEquals(List.of("Doe, J. (2024). Open research systems."), result.getReferences());
    assertEquals("Full paper text for the MVP workflow test.", result.getContent());
    assertEquals("Supported by the Open Research Fund.", result.getFundingStatement());
    assertEquals("No competing interests declared.", result.getConflictOfInterest());
    assertEquals("Data are available on request.", result.getDataAvailability());
    assertEquals("No human subjects were involved.", result.getEthicsStatement());
    assertEquals("manuscript.pdf", result.getManuscriptFiles().get(0).getFileName());
    assertEquals("Supplementary File", result.getSupplementaryFiles().get(0).getFileRole());
    assertEquals(2L, savedAuthors.get().get(0).getUser().getId());
    assertEquals("0000-0002-1825-0097", savedAuthors.get().get(0).getOrcid());
    assertEquals("United States", savedAuthors.get().get(0).getCountry());
    assertEquals(false, savedAuthors.get().get(0).isEqualContribution());
    assertEquals("Conceptualization\nMethodology\nWriting - original draft", savedAuthors.get().get(0).getContributionRoles());
    assertEquals(ExpertIdentityStatus.ORCID_MATCHED, savedAuthors.get().get(0).getIdentityStatus());
    assertEquals(300L, savedAuthors.get().get(0).getExpertProfile().getId());

    ArgumentCaptor<PostType> postTypeCaptor = ArgumentCaptor.forClass(PostType.class);
    verify(postService).createPost(
      any(),
      any(),
      any(),
      any(),
      any(),
      postTypeCaptor.capture(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any()
    );
    assertEquals(PostType.PAPER, postTypeCaptor.getValue());
  }

  @Test
  void submitPaperDerivesPrimaryInstitutionFromFirstAuthor() {
    PostService postService = mock(PostService.class);
    PaperProfileRepository paperProfileRepository = mock(PaperProfileRepository.class);
    PaperAuthorRepository paperAuthorRepository = mock(PaperAuthorRepository.class);
    InstitutionRepository institutionRepository = mock(InstitutionRepository.class);
    AiScreeningResultRepository aiScreeningResultRepository = mock(
      AiScreeningResultRepository.class
    );
    CategoryRepository categoryRepository = mock(CategoryRepository.class);
    TagRepository tagRepository = mock(TagRepository.class);
    UserRepository userRepository = mock(UserRepository.class);
    ExpertProfileRepository expertProfileRepository = mock(ExpertProfileRepository.class);

    PaperService service = new PaperService(
      postService,
      paperProfileRepository,
      paperAuthorRepository,
      mock(PaperAuthorAffiliationRepository.class),
      mock(PaperFundingRecordRepository.class),
      mock(PaperFileRepository.class),
      institutionRepository,
      aiScreeningResultRepository,
      mock(AiScreeningService.class),
      mock(PaperScoreSnapshotRepository.class),
      categoryRepository,
      tagRepository,
      new PaperAccessPolicy(paperAuthorRepository),
      userRepository,
      expertProfileRepository,
      mock(SubscriptionService.class)
    );

    User submitter = new User();
    submitter.setId(1L);
    submitter.setUsername("admin");

    Post post = new Post();
    post.setId(10L);
    post.setAuthor(submitter);

    Institution metadataInstitution = new Institution();
    metadataInstitution.setId(31L);
    metadataInstitution.setName("Metadata University");

    Institution authorInstitution = new Institution();
    authorInstitution.setId(32L);
    authorInstitution.setName("First Author University");

    when(postService.createPost(
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any()
    )).thenReturn(post);
    when(categoryRepository.findByName("Papers")).thenReturn(Optional.empty());
    when(categoryRepository.save(any(Category.class))).thenAnswer(invocation -> {
      Category category = invocation.getArgument(0);
      category.setId(100L);
      return category;
    });
    when(tagRepository.findByName("Research Paper")).thenReturn(Optional.empty());
    when(tagRepository.save(any(Tag.class))).thenAnswer(invocation -> {
      Tag tag = invocation.getArgument(0);
      tag.setId(200L);
      return tag;
    });
    when(institutionRepository.findByNameIgnoreCase("Metadata University")).thenReturn(
      Optional.of(metadataInstitution)
    );
    when(institutionRepository.findByNameIgnoreCase("First Author University")).thenReturn(
      Optional.of(authorInstitution)
    );
    when(expertProfileRepository.findByOrcid(any())).thenReturn(Optional.empty());
    when(expertProfileRepository.findByEmailIgnoreCase(any())).thenReturn(Optional.empty());
    when(expertProfileRepository.save(any(ExpertProfile.class))).thenAnswer(invocation -> {
      ExpertProfile expert = invocation.getArgument(0);
      expert.setId(300L);
      return expert;
    });
    when(paperAuthorRepository.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));
    when(paperProfileRepository.save(any(PaperProfile.class))).thenAnswer(invocation -> {
      PaperProfile paper = invocation.getArgument(0);
      if (paper.getId() == null) {
        paper.setId(20L);
      }
      return paper;
    });
    when(aiScreeningResultRepository.save(any(AiScreeningResult.class))).thenAnswer(invocation -> {
      AiScreeningResult result = invocation.getArgument(0);
      result.setId(40L);
      result.setScreenedAt(LocalDateTime.now());
      return result;
    });

    PaperSubmitRequest request = buildRequest();
    request.setPrimaryInstitutionName("Metadata University");
    request.getAuthors().get(0).setInstitutionName("First Author University");

    service.submitPaper("admin", request);

    ArgumentCaptor<PaperProfile> paperCaptor = ArgumentCaptor.forClass(PaperProfile.class);
    verify(paperProfileRepository, org.mockito.Mockito.atLeastOnce()).save(paperCaptor.capture());
    assertEquals(
      "First Author University",
      paperCaptor.getAllValues().get(0).getPrimaryInstitution().getName()
    );
  }

  @Test
  void submitPaperRejectsAuthorsWithoutCorrespondingAuthor() {
    PaperService service = buildPaperService();
    PaperSubmitRequest request = buildRequest();
    request.getAuthors().get(0).setCorrespondingAuthor(false);

    IllegalArgumentException exception = assertThrows(
      IllegalArgumentException.class,
      () -> service.submitPaper("admin", request)
    );

    assertEquals("At least one corresponding author is required", exception.getMessage());
  }

  @Test
  void submitPaperRejectsCorrespondingAuthorWithoutEmail() {
    PaperService service = buildPaperService();
    PaperSubmitRequest request = buildRequest();
    request.getAuthors().get(0).setEmail(" ");

    IllegalArgumentException exception = assertThrows(
      IllegalArgumentException.class,
      () -> service.submitPaper("admin", request)
    );

    assertEquals("Corresponding author email is required", exception.getMessage());
  }

  @Test
  void submitPaperRejectsSingleCoFirstAuthor() {
    PaperService service = buildPaperService();
    PaperSubmitRequest request = buildRequest();
    request.getAuthors().get(0).setEqualContribution(true);

    IllegalArgumentException exception = assertThrows(
      IllegalArgumentException.class,
      () -> service.submitPaper("admin", request)
    );

    assertEquals("At least two co-first authors are required", exception.getMessage());
  }

  @Test
  void submitPaperLinksAuthorToRegisteredUserByEmail() {
    PostService postService = mock(PostService.class);
    PaperProfileRepository paperProfileRepository = mock(PaperProfileRepository.class);
    PaperAuthorRepository paperAuthorRepository = mock(PaperAuthorRepository.class);
    InstitutionRepository institutionRepository = mock(InstitutionRepository.class);
    AiScreeningResultRepository aiScreeningResultRepository = mock(
      AiScreeningResultRepository.class
    );
    CategoryRepository categoryRepository = mock(CategoryRepository.class);
    TagRepository tagRepository = mock(TagRepository.class);
    UserRepository userRepository = mock(UserRepository.class);
    ExpertProfileRepository expertProfileRepository = mock(ExpertProfileRepository.class);

    PaperService service = new PaperService(
      postService,
      paperProfileRepository,
      paperAuthorRepository,
      mock(PaperAuthorAffiliationRepository.class),
      mock(PaperFundingRecordRepository.class),
      mock(PaperFileRepository.class),
      institutionRepository,
      aiScreeningResultRepository,
      mock(AiScreeningService.class),
      mock(PaperScoreSnapshotRepository.class),
      categoryRepository,
      tagRepository,
      new PaperAccessPolicy(paperAuthorRepository),
      userRepository,
      expertProfileRepository,
      mock(SubscriptionService.class)
    );

    User submitter = new User();
    submitter.setId(1L);
    submitter.setUsername("admin");

    User linkedAuthor = new User();
    linkedAuthor.setId(7L);
    linkedAuthor.setUsername("alice");
    linkedAuthor.setEmail("alice@example.edu");

    Post post = new Post();
    post.setId(10L);
    post.setAuthor(submitter);
    post.setContent("Full paper text for the MVP workflow test.");

    Institution institution = new Institution();
    institution.setId(30L);
    institution.setName("Example University");

    when(postService.createPost(
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any()
    )).thenReturn(post);
    when(categoryRepository.findByName("Papers")).thenReturn(Optional.empty());
    when(categoryRepository.save(any(Category.class))).thenAnswer(invocation -> {
      Category category = invocation.getArgument(0);
      category.setId(100L);
      return category;
    });
    when(tagRepository.findByName("Research Paper")).thenReturn(Optional.empty());
    when(tagRepository.save(any(Tag.class))).thenAnswer(invocation -> {
      Tag tag = invocation.getArgument(0);
      tag.setId(200L);
      return tag;
    });
    when(institutionRepository.findByNameIgnoreCase("Example University")).thenReturn(Optional.of(institution));
    when(userRepository.findByEmail("alice@example.edu")).thenReturn(Optional.of(linkedAuthor));
    when(expertProfileRepository.findByOrcid("0000-0002-1825-0097")).thenReturn(Optional.empty());
    when(expertProfileRepository.findByEmailIgnoreCase("alice@example.edu")).thenReturn(Optional.empty());
    when(expertProfileRepository.save(any(ExpertProfile.class))).thenAnswer(invocation -> {
      ExpertProfile expert = invocation.getArgument(0);
      expert.setId(300L);
      return expert;
    });

    AtomicReference<List<PaperAuthor>> savedAuthors = new AtomicReference<>(List.of());
    when(paperAuthorRepository.saveAll(any())).thenAnswer(invocation -> {
      List<PaperAuthor> authors = invocation.getArgument(0);
      savedAuthors.set(authors);
      return authors;
    });
    when(paperAuthorRepository.findByPaperIdOrderByAuthorOrderAsc(20L)).thenAnswer(invocation ->
      savedAuthors.get()
    );
    when(paperProfileRepository.save(any(PaperProfile.class))).thenAnswer(invocation -> {
      PaperProfile paper = invocation.getArgument(0);
      if (paper.getId() == null) {
        paper.setId(20L);
      }
      return paper;
    });
    when(aiScreeningResultRepository.save(any(AiScreeningResult.class))).thenAnswer(invocation -> {
      AiScreeningResult result = invocation.getArgument(0);
      result.setId(40L);
      result.setScreenedAt(LocalDateTime.now());
      return result;
    });

    PaperDetailDto result = service.submitPaper("admin", buildRequest());

    assertEquals(7L, savedAuthors.get().get(0).getUser().getId());
    assertEquals(ExpertIdentityStatus.ORCID_MATCHED, result.getAuthors().get(0).getIdentityStatus());
  }

  @Test
  void submitPaperRejectsAuthorWithoutDisplayName() {
    PaperService service = buildPaperService();
    PaperSubmitRequest request = buildRequest();
    request.getAuthors().get(0).setDisplayName(" ");

    IllegalArgumentException exception = assertThrows(
      IllegalArgumentException.class,
      () -> service.submitPaper("admin", request)
    );

    assertEquals("Author name is required", exception.getMessage());
  }

  @Test
  void submitPaperAllowsMissingReferences() {
    PostService postService = mock(PostService.class);
    PaperProfileRepository paperProfileRepository = mock(PaperProfileRepository.class);
    PaperAuthorRepository paperAuthorRepository = mock(PaperAuthorRepository.class);
    InstitutionRepository institutionRepository = mock(InstitutionRepository.class);
    AiScreeningResultRepository aiScreeningResultRepository = mock(
      AiScreeningResultRepository.class
    );
    CategoryRepository categoryRepository = mock(CategoryRepository.class);
    TagRepository tagRepository = mock(TagRepository.class);
    UserRepository userRepository = mock(UserRepository.class);
    ExpertProfileRepository expertProfileRepository = mock(ExpertProfileRepository.class);

    PaperService service = new PaperService(
      postService,
      paperProfileRepository,
      paperAuthorRepository,
      mock(PaperAuthorAffiliationRepository.class),
      mock(PaperFundingRecordRepository.class),
      mock(PaperFileRepository.class),
      institutionRepository,
      aiScreeningResultRepository,
      mock(AiScreeningService.class),
      mock(PaperScoreSnapshotRepository.class),
      categoryRepository,
      tagRepository,
      new PaperAccessPolicy(paperAuthorRepository),
      userRepository,
      expertProfileRepository,
      mock(SubscriptionService.class)
    );

    User submitter = new User();
    submitter.setId(1L);
    submitter.setUsername("admin");

    Post post = new Post();
    post.setId(10L);
    post.setAuthor(submitter);
    post.setContent("Full paper text for the MVP workflow test.");

    Institution institution = new Institution();
    institution.setId(30L);
    institution.setName("Example University");

    when(postService.createPost(
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any()
    )).thenReturn(post);
    when(categoryRepository.findByName("Papers")).thenReturn(Optional.empty());
    when(categoryRepository.save(any(Category.class))).thenAnswer(invocation -> {
      Category category = invocation.getArgument(0);
      category.setId(100L);
      return category;
    });
    when(tagRepository.findByName("Research Paper")).thenReturn(Optional.empty());
    when(tagRepository.save(any(Tag.class))).thenAnswer(invocation -> {
      Tag tag = invocation.getArgument(0);
      tag.setId(200L);
      return tag;
    });
    when(institutionRepository.findByNameIgnoreCase("Example University")).thenReturn(Optional.of(institution));
    when(expertProfileRepository.findByOrcid(any())).thenReturn(Optional.empty());
    when(expertProfileRepository.findByEmailIgnoreCase(any())).thenReturn(Optional.empty());
    when(expertProfileRepository.save(any(ExpertProfile.class))).thenAnswer(invocation -> {
      ExpertProfile expert = invocation.getArgument(0);
      expert.setId(300L);
      return expert;
    });
    when(paperAuthorRepository.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));
    when(paperAuthorRepository.findByPaperIdOrderByAuthorOrderAsc(20L)).thenReturn(List.of());
    when(paperProfileRepository.save(any(PaperProfile.class))).thenAnswer(invocation -> {
      PaperProfile paper = invocation.getArgument(0);
      if (paper.getId() == null) {
        paper.setId(20L);
      }
      return paper;
    });
    when(aiScreeningResultRepository.save(any(AiScreeningResult.class))).thenAnswer(invocation -> {
      AiScreeningResult result = invocation.getArgument(0);
      result.setId(40L);
      result.setScreenedAt(LocalDateTime.now());
      return result;
    });

    PaperSubmitRequest request = buildRequest();
    request.setReferences(List.of());

    PaperDetailDto result = service.submitPaper("admin", request);

    assertNotNull(result.getId());
    assertEquals(List.of(), result.getReferences());
  }

  @Test
  void submitPaperRejectsNonContinuousCoFirstAuthors() {
    PaperService service = buildPaperService();
    PaperSubmitRequest request = buildRequest();
    request.getAuthors().get(0).setEqualContribution(true);

    PaperAuthorRequest secondAuthor = new PaperAuthorRequest();
    secondAuthor.setDisplayName("Bob Researcher");
    secondAuthor.setEmail("bob@example.edu");
    secondAuthor.setInstitutionName("Example University");
    secondAuthor.setCountry("United States");
    secondAuthor.setCorrespondingAuthor(false);
    secondAuthor.setEqualContribution(false);

    PaperAuthorRequest thirdAuthor = new PaperAuthorRequest();
    thirdAuthor.setDisplayName("Carol Researcher");
    thirdAuthor.setEmail("carol@example.edu");
    thirdAuthor.setInstitutionName("Example University");
    thirdAuthor.setCountry("United States");
    thirdAuthor.setCorrespondingAuthor(false);
    thirdAuthor.setEqualContribution(true);

    request.setAuthors(List.of(request.getAuthors().get(0), secondAuthor, thirdAuthor));

    IllegalArgumentException exception = assertThrows(
      IllegalArgumentException.class,
      () -> service.submitPaper("admin", request)
    );

    assertEquals("Co-first authors must start from the first author and be continuous", exception.getMessage());
  }

  @Test
  void getPaperDoesNotExposeUnpublishedPaperPublicly() {
    PostService postService = mock(PostService.class);
    PaperProfileRepository paperProfileRepository = mock(PaperProfileRepository.class);
    PaperAuthorRepository paperAuthorRepository = mock(PaperAuthorRepository.class);
    InstitutionRepository institutionRepository = mock(InstitutionRepository.class);
    AiScreeningResultRepository aiScreeningResultRepository = mock(
      AiScreeningResultRepository.class
    );
    PaperScoreSnapshotRepository paperScoreSnapshotRepository = mock(
      PaperScoreSnapshotRepository.class
    );
    CategoryRepository categoryRepository = mock(CategoryRepository.class);
    TagRepository tagRepository = mock(TagRepository.class);
    UserRepository userRepository = mock(UserRepository.class);
    ExpertProfileRepository expertProfileRepository = mock(ExpertProfileRepository.class);

    PaperService service = new PaperService(
      postService,
      paperProfileRepository,
      paperAuthorRepository,
      mock(PaperAuthorAffiliationRepository.class),
      mock(PaperFundingRecordRepository.class),
      mock(PaperFileRepository.class),
      institutionRepository,
      aiScreeningResultRepository,
      mock(AiScreeningService.class),
      paperScoreSnapshotRepository,
      categoryRepository,
      tagRepository,
      new PaperAccessPolicy(paperAuthorRepository),
      userRepository,
      expertProfileRepository,
      mock(SubscriptionService.class)
    );

    PaperProfile paper = buildPublishedPaper(11L, 101L, "Screening Paper", "Information Systems", 0, 0);
    paper.setPublicationStatus(PaperPublicationStatus.SCREENING);
    when(paperProfileRepository.findById(11L)).thenReturn(Optional.of(paper));

    assertThrows(NotFoundException.class, () -> service.getPaper(11L));
  }

  @Test
  void getPaperMarksPostSubscriptionForAuthenticatedViewer() {
    PostService postService = mock(PostService.class);
    PaperProfileRepository paperProfileRepository = mock(PaperProfileRepository.class);
    PaperAuthorRepository paperAuthorRepository = mock(PaperAuthorRepository.class);
    PaperScoreSnapshotRepository paperScoreSnapshotRepository = mock(
      PaperScoreSnapshotRepository.class
    );
    SubscriptionService subscriptionService = mock(SubscriptionService.class);
    PaperService service = new PaperService(
      postService,
      paperProfileRepository,
      paperAuthorRepository,
      mock(PaperAuthorAffiliationRepository.class),
      mock(PaperFundingRecordRepository.class),
      mock(PaperFileRepository.class),
      mock(InstitutionRepository.class),
      mock(AiScreeningResultRepository.class),
      mock(AiScreeningService.class),
      paperScoreSnapshotRepository,
      mock(CategoryRepository.class),
      mock(TagRepository.class),
      new PaperAccessPolicy(paperAuthorRepository),
      mock(UserRepository.class),
      mock(ExpertProfileRepository.class),
      subscriptionService
    );

    PaperProfile paper = buildPublishedPaper(31L, 301L, "Subscribed Paper", "Information Systems", 0, 0);
    when(paperProfileRepository.findById(31L)).thenReturn(Optional.of(paper));
    when(paperAuthorRepository.findByPaperIdOrderByAuthorOrderAsc(31L)).thenReturn(List.of());
    when(paperScoreSnapshotRepository.findByPaperId(31L)).thenReturn(Optional.empty());
    when(subscriptionService.isPostSubscribed("reader", 301L)).thenReturn(true);

    PaperDetailDto result = service.getPaper(31L, "reader");

    assertEquals(true, result.isSubscribed());
  }

  private PaperSubmitRequest buildRequest() {
    PaperAuthorRequest author = new PaperAuthorRequest();
    author.setDisplayName("Alice Researcher");
    author.setEmail("alice@example.edu");
    author.setOrcid("0000-0002-1825-0097");
    author.setInstitutionName("Example University");
    author.setCountry("United States");
    author.setCorrespondingAuthor(true);
    author.setEqualContribution(false);
    author.setContributionRoles(List.of("Conceptualization", "Methodology", "Writing - original draft"));

    PaperSubmitRequest request = new PaperSubmitRequest();
    request.setTitle("A Test Paper for MVP Workflow");
    request.setAbstractText("This abstract exists to test paper submission.");
    request.setKeywords(List.of("paper", "mvp", "test"));
    request.setReferences(List.of("Doe, J. (2024). Open research systems."));
    request.setSubjectArea("Information Systems");
    request.setPaperType("Research Article");
    request.setContent("Full paper text for the MVP workflow test.");
    request.setPrimaryInstitutionName("Example University");
    request.setAuthors(List.of(author));
    request.setFundingStatement("Supported by the Open Research Fund.");
    request.setConflictOfInterest("No competing interests declared.");
    request.setDataAvailability("Data are available on request.");
    request.setEthicsStatement("No human subjects were involved.");
    request.setManuscriptFiles(
      List.of(new PaperFileRecordDto("manuscript.pdf", "application/pdf", 120_000L, "Manuscript"))
    );
    request.setSupplementaryFiles(
      List.of(new PaperFileRecordDto("appendix.csv", "text/csv", 12_000L, "Supplementary File"))
    );
    return request;
  }

  private PaperService buildPaperService() {
    PaperAuthorRepository paperAuthorRepository = mock(PaperAuthorRepository.class);
    return new PaperService(
      mock(PostService.class),
      mock(PaperProfileRepository.class),
      paperAuthorRepository,
      mock(PaperAuthorAffiliationRepository.class),
      mock(PaperFundingRecordRepository.class),
      mock(PaperFileRepository.class),
      mock(InstitutionRepository.class),
      mock(AiScreeningResultRepository.class),
      mock(AiScreeningService.class),
      mock(PaperScoreSnapshotRepository.class),
      mock(CategoryRepository.class),
      mock(TagRepository.class),
      new PaperAccessPolicy(paperAuthorRepository),
      mock(UserRepository.class),
      mock(ExpertProfileRepository.class),
      mock(SubscriptionService.class)
    );
  }

  private PaperProfile buildPublishedPaper(
    Long paperId,
    Long postId,
    String title,
    String subjectArea,
    double score,
    int ratingCount
  ) {
    User author = new User();
    author.setId(postId + 1000);
    author.setUsername("author" + postId);

    Post post = new Post();
    post.setId(postId);
    post.setTitle(title);
    post.setContent(title + " content");
    post.setAuthor(author);
    post.setCommentCount(ratingCount);
    post.setViews(ratingCount * 10L);

    PaperProfile paper = new PaperProfile();
    paper.setId(paperId);
    paper.setPost(post);
    paper.setTitle(title);
    paper.setAbstractText(title + " abstract");
    paper.setSubjectArea(subjectArea);
    paper.setPublicationStatus(PaperPublicationStatus.PUBLISHED);
    paper.setScreeningStatus(PaperScreeningStatus.PASSED);
    paper.setPublishedAt(LocalDateTime.now().minusHours(ratingCount));
    return paper;
  }

  private PaperScoreSnapshot buildSnapshot(Long paperId, double compositeScore, int ratingCount) {
    PaperProfile paper = new PaperProfile();
    paper.setId(paperId);

    PaperScoreSnapshot snapshot = new PaperScoreSnapshot();
    snapshot.setPaper(paper);
    snapshot.setCompositeScore(compositeScore);
    snapshot.setAverageOverallScore(compositeScore);
    snapshot.setRatingCount(ratingCount);
    return snapshot;
  }
}
