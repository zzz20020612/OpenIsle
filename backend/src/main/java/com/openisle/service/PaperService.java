package com.openisle.service;

import com.openisle.dto.AiScreeningDto;
import com.openisle.dto.PaperAuthorDto;
import com.openisle.dto.PaperAuthorRequest;
import com.openisle.dto.PaperDetailDto;
import com.openisle.dto.PaperFileRecordDto;
import com.openisle.dto.PaperFilterOptionsDto;
import com.openisle.dto.PaperScoreSnapshotDto;
import com.openisle.dto.PaperSubmitRequest;
import com.openisle.dto.PaperSummaryDto;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
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
import com.openisle.model.PostVisibleScopeType;
import com.openisle.model.Tag;
import com.openisle.repository.AiScreeningResultRepository;
import com.openisle.repository.CategoryRepository;
import com.openisle.repository.ExpertProfileRepository;
import com.openisle.repository.InstitutionRepository;
import com.openisle.repository.PaperAuthorRepository;
import com.openisle.repository.PaperProfileRepository;
import com.openisle.repository.PaperScoreSnapshotRepository;
import com.openisle.repository.TagRepository;
import com.openisle.repository.UserRepository;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Objects;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class PaperService {

  private static final String DEFAULT_PAPER_CATEGORY = "Papers";
  private static final String DEFAULT_PAPER_TAG = "Research Paper";
  private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

  private final PostService postService;
  private final PaperProfileRepository paperProfileRepository;
  private final PaperAuthorRepository paperAuthorRepository;
  private final InstitutionRepository institutionRepository;
  private final AiScreeningResultRepository aiScreeningResultRepository;
  private final MockAiScreeningService mockAiScreeningService;
  private final PaperScoreSnapshotRepository paperScoreSnapshotRepository;
  private final CategoryRepository categoryRepository;
  private final TagRepository tagRepository;
  private final PaperAccessPolicy paperAccessPolicy;
  private final UserRepository userRepository;
  private final ExpertProfileRepository expertProfileRepository;
  private final SubscriptionService subscriptionService;

  @Transactional
  public PaperDetailDto submitPaper(String username, PaperSubmitRequest request) {
    validateSubmitRequest(request);
    Long categoryId = resolvePaperCategoryId(request.getCategoryId());
    List<Long> tagIds = resolvePaperTagIds(request.getTagIds());

    Post post = postService.createPost(
      username,
      categoryId,
      request.getTitle(),
      request.getContent(),
      tagIds,
      PostType.PAPER,
      PostVisibleScopeType.ALL,
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null
    );

    Institution primaryInstitution = resolvePrimaryInstitution(request);

    PaperProfile paper = new PaperProfile();
    paper.setPost(post);
    paper.setTitle(request.getTitle());
    paper.setAbstractText(request.getAbstractText());
    paper.setKeywords(serializeList(request.getKeywords()));
    paper.setReferencesText(serializeList(request.getReferences()));
    paper.setManuscriptFiles(serializeFileRecords(request.getManuscriptFiles()));
    paper.setSupplementaryFiles(serializeFileRecords(request.getSupplementaryFiles()));
    paper.setSubjectArea(request.getSubjectArea());
    paper.setPaperType(request.getPaperType());
    paper.setFundingStatement(cleanOptionalText(request.getFundingStatement()));
    paper.setConflictOfInterest(cleanOptionalText(request.getConflictOfInterest()));
    paper.setDataAvailability(cleanOptionalText(request.getDataAvailability()));
    paper.setEthicsStatement(cleanOptionalText(request.getEthicsStatement()));
    paper.setPrimaryInstitution(primaryInstitution);
    paper.setCreatedBy(post.getAuthor());
    paper.setPublicationStatus(PaperPublicationStatus.SCREENING);
    paper.setScreeningStatus(PaperScreeningStatus.SCREENING);
    paper = paperProfileRepository.save(paper);

    saveAuthors(paper, request);

    AiScreeningResult screening = mockAiScreeningService.screen(paper);
    screening = aiScreeningResultRepository.save(screening);

    if (screening.getStatus() == PaperScreeningStatus.PASSED) {
      paper.setScreeningStatus(PaperScreeningStatus.PASSED);
      paper.setPublicationStatus(PaperPublicationStatus.PUBLISHED);
      paper.setPublishedAt(LocalDateTime.now());
      paper = paperProfileRepository.save(paper);
    }

    return toDetailDto(paper, screening, username);
  }

  @Transactional(readOnly = true)
  public List<PaperSummaryDto> listPublishedPapers(
    int page,
    int pageSize,
    String subject,
    Double minScore,
    String sort
  ) {
    List<PaperProfile> papers;
    if (subject != null && !subject.isBlank()) {
      papers =
        paperProfileRepository.findByPublicationStatusAndSubjectAreaIgnoreCaseOrderByPublishedAtDesc(
          PaperPublicationStatus.PUBLISHED,
          subject.trim(),
          PageRequest.of(Math.max(page, 0), Math.max(pageSize, 1))
        );
    } else {
      papers =
        paperProfileRepository.findByPublicationStatusOrderByPublishedAtDesc(
          PaperPublicationStatus.PUBLISHED,
          PageRequest.of(Math.max(page, 0), Math.max(pageSize, 1))
        );
    }

    return papers
      .stream()
      .filter(paperAccessPolicy::canAppearInFeed)
      .map(this::toSummaryDto)
      .filter(dto ->
        minScore == null ||
        (dto.getScoreSnapshot() != null && dto.getScoreSnapshot().getCompositeScore() >= minScore)
      )
      .sorted(resolvePaperSort(sort))
      .toList();
  }

  @Transactional(readOnly = true)
  public PaperFilterOptionsDto getFilterOptions() {
    PaperFilterOptionsDto dto = new PaperFilterOptionsDto();
    dto.setSubjects(
      paperProfileRepository
        .findDistinctByPublicationStatusOrderBySubjectAreaAsc(PaperPublicationStatus.PUBLISHED)
        .stream()
        .map(PaperProfile::getSubjectArea)
        .filter(Objects::nonNull)
        .map(String::trim)
        .filter(value -> !value.isBlank())
        .distinct()
        .toList()
    );
    return dto;
  }

  @Transactional(readOnly = true)
  public PaperDetailDto getPaper(Long paperId) {
    return getPaper(paperId, null);
  }

  @Transactional(readOnly = true)
  public PaperDetailDto getPaper(Long paperId, String viewer) {
    PaperProfile paper = paperProfileRepository
      .findById(paperId)
      .orElseThrow(() -> new NotFoundException("Paper not found"));
    if (!paperAccessPolicy.canAppearInFeed(paper)) {
      throw new NotFoundException("Paper not found");
    }
    AiScreeningResult screening = aiScreeningResultRepository
      .findFirstByPaperIdOrderByScreenedAtDesc(paperId)
      .orElse(null);
    return toDetailDto(paper, screening, viewer);
  }

  private void validateSubmitRequest(PaperSubmitRequest request) {
    if (request.getTitle() == null || request.getTitle().isBlank()) {
      throw new IllegalArgumentException("Title is required");
    }
    if (request.getAbstractText() == null || request.getAbstractText().isBlank()) {
      throw new IllegalArgumentException("Abstract is required");
    }
    if (request.getContent() == null || request.getContent().isBlank()) {
      throw new IllegalArgumentException("Full text is required");
    }
    if (request.getSubjectArea() == null || request.getSubjectArea().isBlank()) {
      throw new IllegalArgumentException("Subject area is required");
    }
    if (request.getKeywords() == null || request.getKeywords().isEmpty()) {
      throw new IllegalArgumentException("At least one keyword is required");
    }
    if (request.getAuthors() == null || request.getAuthors().isEmpty()) {
      throw new IllegalArgumentException("At least one author is required");
    }
    boolean hasCorrespondingAuthor = false;
    for (PaperAuthorRequest author : request.getAuthors()) {
      if (author == null || cleanOptionalText(author.getDisplayName()) == null) {
        throw new IllegalArgumentException("Author name is required");
      }
      if (Boolean.TRUE.equals(author.getCorrespondingAuthor())) {
        hasCorrespondingAuthor = true;
        if (cleanOptionalText(author.getEmail()) == null) {
          throw new IllegalArgumentException("Corresponding author email is required");
        }
      }
    }
    if (!hasCorrespondingAuthor) {
      throw new IllegalArgumentException("At least one corresponding author is required");
    }
    validateCoFirstAuthors(request.getAuthors());
  }

  private void validateCoFirstAuthors(List<PaperAuthorRequest> authors) {
    int coFirstAuthorCount = 0;
    boolean foundNonCoFirstAuthor = false;
    for (PaperAuthorRequest author : authors) {
      boolean coFirstAuthor = Boolean.TRUE.equals(author.getEqualContribution());
      if (coFirstAuthor) {
        coFirstAuthorCount++;
        if (foundNonCoFirstAuthor) {
          throw new IllegalArgumentException(
            "Co-first authors must start from the first author and be continuous"
          );
        }
      } else {
        foundNonCoFirstAuthor = true;
      }
    }
    if (coFirstAuthorCount == 1) {
      throw new IllegalArgumentException("At least two co-first authors are required");
    }
  }

  private Institution getOrCreateInstitution(String institutionName) {
    if (institutionName == null || institutionName.isBlank()) {
      return null;
    }
    String normalizedName = institutionName.trim();
    return institutionRepository
      .findByNameIgnoreCase(normalizedName)
      .orElseGet(() -> {
        Institution institution = new Institution();
        institution.setName(normalizedName);
        institution.setType("UNSPECIFIED");
        return institutionRepository.save(institution);
      });
  }

  private Institution resolvePrimaryInstitution(PaperSubmitRequest request) {
    if (request.getAuthors() == null || request.getAuthors().isEmpty()) {
      return null;
    }

    String firstAuthorInstitution = cleanOptionalText(request.getAuthors().get(0).getInstitutionName());
    if (firstAuthorInstitution != null) {
      return getOrCreateInstitution(firstAuthorInstitution);
    }

    return request
      .getAuthors()
      .stream()
      .filter(author -> Boolean.TRUE.equals(author.getCorrespondingAuthor()))
      .map(PaperAuthorRequest::getInstitutionName)
      .map(PaperService::cleanOptionalText)
      .filter(Objects::nonNull)
      .findFirst()
      .map(this::getOrCreateInstitution)
      .orElse(null);
  }

  private void saveAuthors(PaperProfile paper, PaperSubmitRequest request) {
    List<PaperAuthor> authors = new ArrayList<>();
    for (int i = 0; i < request.getAuthors().size(); i++) {
      PaperAuthorRequest authorRequest = request.getAuthors().get(i);
      Institution institution = getOrCreateInstitution(authorRequest.getInstitutionName());
      com.openisle.model.User linkedUser = resolveAuthorUser(authorRequest.getEmail());
      ExpertProfile expertProfile = resolveExpertProfile(authorRequest, institution, linkedUser);
      PaperAuthor author = new PaperAuthor();
      author.setPaper(paper);
      author.setDisplayName(authorRequest.getDisplayName());
      author.setEmail(authorRequest.getEmail());
      author.setOrcid(cleanOptionalText(authorRequest.getOrcid()));
      author.setCountry(cleanOptionalText(authorRequest.getCountry()));
      author.setUser(linkedUser);
      author.setExpertProfile(expertProfile);
      author.setIdentityStatus(resolveIdentityStatus(authorRequest, linkedUser, expertProfile));
      author.setAuthorOrder(i + 1);
      author.setCorrespondingAuthor(Boolean.TRUE.equals(authorRequest.getCorrespondingAuthor()));
      author.setEqualContribution(Boolean.TRUE.equals(authorRequest.getEqualContribution()));
      author.setContributionRoles(serializeList(authorRequest.getContributionRoles()));
      author.setInstitution(institution);
      authors.add(author);
    }
    paperAuthorRepository.saveAll(authors);
  }

  private com.openisle.model.User resolveAuthorUser(String email) {
    if (email == null || email.isBlank()) {
      return null;
    }
    return userRepository.findByEmail(email.trim()).orElse(null);
  }

  private ExpertProfile resolveExpertProfile(
    PaperAuthorRequest authorRequest,
    Institution institution,
    com.openisle.model.User linkedUser
  ) {
    String orcid = cleanOptionalText(authorRequest.getOrcid());
    String email = cleanOptionalText(authorRequest.getEmail());
    ExpertProfile expertProfile = null;
    if (orcid != null) {
      expertProfile = expertProfileRepository.findByOrcid(orcid).orElse(null);
    }
    if (expertProfile == null && email != null) {
      expertProfile = expertProfileRepository.findByEmailIgnoreCase(email).orElse(null);
    }
    if (expertProfile == null) {
      expertProfile = new ExpertProfile();
      expertProfile.setDisplayName(authorRequest.getDisplayName());
    }
    expertProfile.setUser(linkedUser != null ? linkedUser : expertProfile.getUser());
    expertProfile.setDisplayName(cleanOptionalText(authorRequest.getDisplayName()));
    expertProfile.setEmail(email);
    expertProfile.setOrcid(orcid);
    expertProfile.setPrimaryInstitution(institution);
    expertProfile.setCountry(cleanOptionalText(authorRequest.getCountry()));
    expertProfile.setIdentityStatus(resolveIdentityStatus(authorRequest, linkedUser, expertProfile));
    return expertProfileRepository.save(expertProfile);
  }

  private ExpertIdentityStatus resolveIdentityStatus(
    PaperAuthorRequest authorRequest,
    com.openisle.model.User linkedUser,
    ExpertProfile expertProfile
  ) {
    if (expertProfile != null && expertProfile.getIdentityStatus() == ExpertIdentityStatus.VERIFIED) {
      return ExpertIdentityStatus.VERIFIED;
    }
    if (cleanOptionalText(authorRequest.getOrcid()) != null && expertProfile != null && expertProfile.getId() != null) {
      return ExpertIdentityStatus.ORCID_MATCHED;
    }
    if (linkedUser != null) {
      return ExpertIdentityStatus.EMAIL_MATCHED;
    }
    return ExpertIdentityStatus.UNMATCHED;
  }

  private PaperSummaryDto toSummaryDto(PaperProfile paper) {
    PaperSummaryDto dto = new PaperSummaryDto();
    dto.setId(paper.getId());
    dto.setPostId(paper.getPost().getId());
    dto.setTitle(paper.getTitle());
    dto.setAbstractText(paper.getAbstractText());
    dto.setKeywords(deserializeList(paper.getKeywords()));
    dto.setSubjectArea(paper.getSubjectArea());
    dto.setPaperType(paper.getPaperType());
    dto.setPublicationStatus(paper.getPublicationStatus());
    dto.setScreeningStatus(paper.getScreeningStatus());
    dto.setPublishedAt(paper.getPublishedAt());
    dto.setFeatured(paper.getPost().getPinnedAt() != null);
    dto.setRssExcluded(Boolean.TRUE.equals(paper.getPost().getRssExcluded()));
    dto.setCommentCount(paper.getPost().getCommentCount());
    dto.setViews(paper.getPost().getViews());
    dto.setPrimaryInstitutionName(
      paper.getPrimaryInstitution() != null ? paper.getPrimaryInstitution().getName() : null
    );
    dto.setAuthors(
      paperAuthorRepository
        .findByPaperIdOrderByAuthorOrderAsc(paper.getId())
        .stream()
        .map(this::toAuthorDto)
        .toList()
    );
    dto.setScoreSnapshot(getScoreSnapshotDto(paper.getId()));
    return dto;
  }

  private Comparator<PaperSummaryDto> resolvePaperSort(String sort) {
    Comparator<PaperSummaryDto> featuredFirst = Comparator
      .comparing(PaperSummaryDto::isFeatured)
      .reversed();
    if ("score".equalsIgnoreCase(sort)) {
      return featuredFirst.thenComparing(
        Comparator
        .comparingDouble((PaperSummaryDto dto) ->
          dto.getScoreSnapshot() != null ? dto.getScoreSnapshot().getCompositeScore() : 0.0
        )
        .reversed()
        .thenComparing(PaperSummaryDto::getPublishedAt, Comparator.nullsLast(Comparator.reverseOrder()))
      );
    }
    return featuredFirst.thenComparing(
      PaperSummaryDto::getPublishedAt,
      Comparator.nullsLast(Comparator.reverseOrder())
    );
  }

  private PaperDetailDto toDetailDto(PaperProfile paper, AiScreeningResult screening) {
    return toDetailDto(paper, screening, null);
  }

  private PaperDetailDto toDetailDto(
    PaperProfile paper,
    AiScreeningResult screening,
    String viewer
  ) {
    PaperSummaryDto summary = toSummaryDto(paper);
    PaperDetailDto dto = new PaperDetailDto();
    dto.setId(summary.getId());
    dto.setPostId(summary.getPostId());
    dto.setTitle(summary.getTitle());
    dto.setAbstractText(summary.getAbstractText());
    dto.setSubjectArea(summary.getSubjectArea());
    dto.setPaperType(summary.getPaperType());
    dto.setPublicationStatus(summary.getPublicationStatus());
    dto.setScreeningStatus(summary.getScreeningStatus());
    dto.setPrimaryInstitutionName(summary.getPrimaryInstitutionName());
    dto.setAuthors(summary.getAuthors());
    dto.setPublishedAt(summary.getPublishedAt());
    dto.setFeatured(summary.isFeatured());
    dto.setRssExcluded(summary.isRssExcluded());
    dto.setScoreSnapshot(summary.getScoreSnapshot());
    dto.setKeywords(summary.getKeywords());
    dto.setReferences(deserializeList(paper.getReferencesText()));
    dto.setContent(paper.getPost().getContent());
    dto.setFundingStatement(paper.getFundingStatement());
    dto.setConflictOfInterest(paper.getConflictOfInterest());
    dto.setDataAvailability(paper.getDataAvailability());
    dto.setEthicsStatement(paper.getEthicsStatement());
    dto.setManuscriptFiles(deserializeFileRecords(paper.getManuscriptFiles()));
    dto.setSupplementaryFiles(deserializeFileRecords(paper.getSupplementaryFiles()));
    dto.setAuthorInstitutions(
      paperAuthorRepository
        .findByPaperIdOrderByAuthorOrderAsc(paper.getId())
        .stream()
        .map(author -> author.getInstitution() != null ? author.getInstitution().getName() : null)
        .filter(Objects::nonNull)
        .toList()
    );
    dto.setScreening(toScreeningDto(screening));
    dto.setSubscribed(
      viewer != null && subscriptionService.isPostSubscribed(viewer, paper.getPost().getId())
    );
    return dto;
  }

  private PaperScoreSnapshotDto getScoreSnapshotDto(Long paperId) {
    return paperScoreSnapshotRepository
      .findByPaperId(paperId)
      .map(this::toScoreSnapshotDto)
      .orElseGet(PaperService::emptyScoreSnapshotDto);
  }

  private PaperAuthorDto toAuthorDto(PaperAuthor author) {
    PaperAuthorDto dto = new PaperAuthorDto();
    dto.setId(author.getId());
    dto.setAuthorOrder(author.getAuthorOrder());
    dto.setDisplayName(author.getDisplayName());
    dto.setInstitutionId(author.getInstitution() != null ? author.getInstitution().getId() : null);
    dto.setInstitution(author.getInstitution() != null ? author.getInstitution().getName() : null);
    dto.setCountry(author.getCountry());
    dto.setCorrespondingAuthor(author.isCorrespondingAuthor());
    dto.setEqualContribution(author.isEqualContribution());
    dto.setIdentityStatus(author.getIdentityStatus());
    dto.setExpertProfileId(
      author.getExpertProfile() != null ? author.getExpertProfile().getId() : null
    );
    dto.setUserId(author.getUser() != null ? author.getUser().getId() : null);
    return dto;
  }

  private PaperScoreSnapshotDto toScoreSnapshotDto(PaperScoreSnapshot snapshot) {
    PaperScoreSnapshotDto dto = new PaperScoreSnapshotDto();
    dto.setRatingCount(snapshot.getRatingCount());
    dto.setAverageOverallScore(snapshot.getAverageOverallScore());
    dto.setAverageInnovationScore(snapshot.getAverageInnovationScore());
    dto.setAverageMethodScore(snapshot.getAverageMethodScore());
    dto.setAverageImpactScore(snapshot.getAverageImpactScore());
    dto.setCompositeScore(snapshot.getCompositeScore());
    return dto;
  }

  private static PaperScoreSnapshotDto emptyScoreSnapshotDto() {
    return new PaperScoreSnapshotDto();
  }

  private static String serializeList(List<String> values) {
    if (values == null) {
      return null;
    }
    return values
      .stream()
      .filter(Objects::nonNull)
      .map(String::trim)
      .filter(value -> !value.isBlank())
      .distinct()
      .reduce((left, right) -> left + "\n" + right)
      .orElse(null);
  }

  private static List<String> deserializeList(String value) {
    if (value == null || value.isBlank()) {
      return List.of();
    }
    return value
      .lines()
      .map(String::trim)
      .filter(line -> !line.isBlank())
      .toList();
  }

  private Long resolvePaperCategoryId(Long requestedCategoryId) {
    if (requestedCategoryId != null && categoryRepository.existsById(requestedCategoryId)) {
      return requestedCategoryId;
    }
    return categoryRepository
      .findByName(DEFAULT_PAPER_CATEGORY)
      .orElseGet(() -> {
        Category category = new Category();
        category.setName(DEFAULT_PAPER_CATEGORY);
        category.setIcon("book-open");
        category.setSmallIcon("book");
        category.setDescription("Default category for published research papers.");
        return categoryRepository.save(category);
      })
      .getId();
  }

  private List<Long> resolvePaperTagIds(List<Long> requestedTagIds) {
    if (requestedTagIds != null && !requestedTagIds.isEmpty()) {
      List<Tag> tags = tagRepository.findAllById(requestedTagIds);
      if (!tags.isEmpty()) {
        return tags.stream().map(Tag::getId).toList();
      }
    }
    Long defaultTagId = tagRepository
      .findByName(DEFAULT_PAPER_TAG)
      .orElseGet(() -> {
        Tag tag = new Tag();
        tag.setName(DEFAULT_PAPER_TAG);
        tag.setIcon("article");
        tag.setSmallIcon("article");
        tag.setDescription("Default tag for paper records.");
        tag.setApproved(true);
        return tagRepository.save(tag);
      })
      .getId();
    return List.of(defaultTagId);
  }

  private static String cleanOptionalText(String value) {
    if (value == null || value.isBlank()) {
      return null;
    }
    return value.trim();
  }

  private static String serializeFileRecords(List<PaperFileRecordDto> records) {
    if (records == null || records.isEmpty()) {
      return null;
    }
    return records
      .stream()
      .filter(Objects::nonNull)
      .filter(record -> record.getFileName() != null && !record.getFileName().isBlank())
      .map(record -> {
        try {
          return OBJECT_MAPPER.writeValueAsString(record);
        } catch (JsonProcessingException exception) {
          throw new IllegalArgumentException("Unable to serialize paper file record", exception);
        }
      })
      .reduce((left, right) -> left + "\n" + right)
      .orElse(null);
  }

  private static List<PaperFileRecordDto> deserializeFileRecords(String value) {
    if (value == null || value.isBlank()) {
      return List.of();
    }
    return value
      .lines()
      .map(String::trim)
      .filter(line -> !line.isBlank())
      .map(line -> {
        try {
          return OBJECT_MAPPER.readValue(line, PaperFileRecordDto.class);
        } catch (JsonProcessingException exception) {
          throw new IllegalArgumentException("Unable to deserialize paper file record", exception);
        }
      })
      .toList();
  }

  private AiScreeningDto toScreeningDto(AiScreeningResult screening) {
    if (screening == null) {
      return null;
    }
    AiScreeningDto dto = new AiScreeningDto();
    dto.setStatus(screening.getStatus());
    dto.setRiskLevel(screening.getRiskLevel());
    dto.setDetectedSubjectArea(screening.getDetectedSubjectArea());
    dto.setDetectedPaperType(screening.getDetectedPaperType());
    dto.setSummary(screening.getSummary());
    dto.setIssuesJson(screening.getIssuesJson());
    dto.setScreenedAt(screening.getScreenedAt());
    return dto;
  }
}
