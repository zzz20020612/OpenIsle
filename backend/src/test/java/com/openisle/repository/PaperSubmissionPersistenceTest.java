package com.openisle.repository;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.openisle.model.Category;
import com.openisle.model.Institution;
import com.openisle.model.PaperAuthor;
import com.openisle.model.PaperAuthorAffiliation;
import com.openisle.model.PaperFile;
import com.openisle.model.PaperFileRole;
import com.openisle.model.PaperFileVisibility;
import com.openisle.model.PaperFundingRecord;
import com.openisle.model.PaperProfile;
import com.openisle.model.PaperSubmissionDraft;
import com.openisle.model.PaperSubmissionDraftStatus;
import com.openisle.model.PaperSubmissionFile;
import com.openisle.model.PaperUploadStatus;
import com.openisle.model.Post;
import com.openisle.model.PostType;
import com.openisle.model.User;
import jakarta.persistence.EntityManager;
import java.time.LocalDateTime;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;

@DataJpaTest
class PaperSubmissionPersistenceTest {

  @Autowired
  private EntityManager entityManager;

  @Autowired
  private UserRepository userRepository;

  @Autowired
  private CategoryRepository categoryRepository;

  @Autowired
  private PostRepository postRepository;

  @Autowired
  private PaperProfileRepository paperProfileRepository;

  @Autowired
  private InstitutionRepository institutionRepository;

  @Autowired
  private PaperAuthorRepository paperAuthorRepository;

  @Autowired
  private PaperSubmissionDraftRepository draftRepository;

  @Autowired
  private PaperSubmissionFileRepository submissionFileRepository;

  @Autowired
  private PaperAuthorAffiliationRepository affiliationRepository;

  @Autowired
  private PaperFundingRecordRepository fundingRecordRepository;

  @Autowired
  private PaperFileRepository paperFileRepository;

  @Test
  void persistsVersionedDraftAndFindsLatestInProgressDraftForOwner() {
    User owner = createUser("draft-owner");
    User otherUser = createUser("other-user");

    createDraft(owner, "older draft");
    PaperSubmissionDraft latestDraft = createDraft(owner, "latest draft");
    PaperSubmissionDraft submittedDraft = createDraft(owner, "submitted draft");
    submittedDraft.setStatus(PaperSubmissionDraftStatus.SUBMITTED);
    draftRepository.saveAndFlush(submittedDraft);
    createDraft(otherUser, "other user's draft");

    PaperSubmissionDraft found = draftRepository
      .findFirstByOwnerIdAndStatusOrderByUpdatedAtDescIdDesc(
        owner.getId(),
        PaperSubmissionDraftStatus.IN_PROGRESS
      )
      .orElseThrow();

    assertEquals(latestDraft.getId(), found.getId());
    assertEquals(owner.getId(), found.getOwner().getId());
    assertEquals("Research Article", found.getManuscriptType());
    assertEquals("{\"title\":\"latest draft\"}", found.getFormDataJson());
    assertEquals("details", found.getCurrentSection());
    assertEquals(PaperSubmissionDraftStatus.IN_PROGRESS, found.getStatus());
    assertNull(found.getSubmittedPaper());
    assertNull(found.getIdempotencyKey());
    assertEquals(0L, found.getVersion());
    assertNotNull(found.getCreatedAt());
    assertNotNull(found.getUpdatedAt());

    found.setCurrentSection("files");
    draftRepository.saveAndFlush(found);

    assertEquals(1L, found.getVersion());
  }

  @Test
  void returnsDraftFilesBySortOrderThenId() {
    User owner = createUser("file-owner");
    PaperSubmissionDraft draft = createDraft(owner, "file draft");

    submissionFileRepository.save(createSubmissionFile(draft, "first.docx", 10));
    submissionFileRepository.save(createSubmissionFile(draft, "second.docx", 10));
    submissionFileRepository.save(createSubmissionFile(draft, "third.docx", 20));

    List<PaperSubmissionFile> files = submissionFileRepository
      .findByDraftIdOrderBySortOrderAscIdAsc(draft.getId());

    assertEquals(
      List.of("first.docx", "second.docx", "third.docx"),
      files.stream().map(PaperSubmissionFile::getDisplayName).toList()
    );
  }

  @Test
  void returnsTwoAuthorAffiliationsInOrderWithOnePrimary() {
    User owner = createUser("author-owner");
    PaperProfile paper = createPaper(owner, "Affiliation Paper");
    PaperAuthor author = createAuthor(paper, createInstitution("Legacy Institution"));

    Institution primaryInstitution = createInstitution("Primary University");
    Institution secondaryInstitution = createInstitution("Secondary University");
    affiliationRepository.save(
      createAffiliation(author, primaryInstitution, "Primary University", true, 10)
    );
    affiliationRepository.save(
      createAffiliation(author, secondaryInstitution, "Secondary University", false, 20)
    );

    List<PaperAuthorAffiliation> affiliations = affiliationRepository
      .findByPaperAuthorIdOrderByDisplayOrderAscIdAsc(author.getId());

    assertEquals(2, affiliations.size());
    assertEquals(
      List.of("Primary University", "Secondary University"),
      affiliations.stream().map(PaperAuthorAffiliation::getOrganizationName).toList()
    );
    assertEquals(
      1L,
      affiliations.stream().filter(PaperAuthorAffiliation::isPrimaryAffiliation).count()
    );
  }

  @Test
  void returnsFundingRecordsByDisplayOrderThenId() {
    User owner = createUser("funding-owner");
    PaperProfile paper = createPaper(owner, "Funding Paper");

    fundingRecordRepository.save(createFundingRecord(paper, "First Funder", 10));
    fundingRecordRepository.save(createFundingRecord(paper, "Second Funder", 10));
    fundingRecordRepository.save(createFundingRecord(paper, "Third Funder", 20));

    List<PaperFundingRecord> records = fundingRecordRepository
      .findByPaperIdOrderByDisplayOrderAscIdAsc(paper.getId());

    assertEquals(
      List.of("First Funder", "Second Funder", "Third Funder"),
      records.stream().map(PaperFundingRecord::getFunderName).toList()
    );
  }

  @Test
  void returnsFinalFilesBySortOrderThenId() {
    User owner = createUser("final-file-owner");
    PaperProfile paper = createPaper(owner, "File Paper");

    paperFileRepository.save(createPaperFile(paper, "first.pdf", 10));
    paperFileRepository.save(createPaperFile(paper, "second.pdf", 10));
    paperFileRepository.save(createPaperFile(paper, "third.pdf", 20));

    List<PaperFile> files = paperFileRepository
      .findByPaperIdOrderBySortOrderAscIdAsc(paper.getId());

    assertEquals(
      List.of("first.pdf", "second.pdf", "third.pdf"),
      files.stream().map(PaperFile::getDisplayName).toList()
    );
    assertTrue(files.stream().allMatch(file -> file.getViewCount() == 0L));
    assertTrue(files.stream().allMatch(file -> file.getDownloadCount() == 0L));
  }

  @Test
  void persistsProfileDeclarationsAndStructuredAuthorName() {
    User owner = createUser("profile-owner");
    Institution institution = createInstitution("Analytical Engine Institute");
    PaperProfile paper = createPaper(owner, "Structured Author Paper");
    PaperAuthor author = createAuthor(paper, institution);
    Long paperId = paper.getId();
    Long authorId = author.getId();

    entityManager.flush();
    entityManager.clear();

    PaperProfile reloadedPaper = paperProfileRepository.findById(paperId).orElseThrow();
    PaperAuthor reloadedAuthor = paperAuthorRepository.findById(authorId).orElseThrow();

    assertEquals("Previously posted as a preprint.", reloadedPaper.getPreprintStatement());
    assertEquals("AI assisted language editing.", reloadedPaper.getAiUseDisclosure());
    assertEquals("For platform staff only.", reloadedPaper.getPrivateComments());
    assertTrue(reloadedPaper.isAllAuthorsConsent());
    assertTrue(reloadedPaper.isOriginalityConfirmed());
    assertTrue(reloadedPaper.isRightsConfirmed());
    assertTrue(reloadedPaper.isCorrespondingAuthorContactConfirmed());
    assertEquals(
      LocalDateTime.of(2026, 7, 12, 12, 0),
      reloadedPaper.getCorrespondingAuthorContactConfirmedAt()
    );
    assertEquals(owner.getId(), reloadedPaper.getCorrespondingAuthorContactConfirmedBy().getId());

    assertEquals("Ada Lovelace", reloadedAuthor.getDisplayName());
    assertEquals(institution.getId(), reloadedAuthor.getInstitution().getId());
    assertEquals("Ada", reloadedAuthor.getGivenName());
    assertEquals("Byron", reloadedAuthor.getMiddleName());
    assertEquals("Lovelace", reloadedAuthor.getFamilyName());
    assertEquals("Author", reloadedAuthor.getAuthorRole());
  }

  private User createUser(String username) {
    User user = new User();
    user.setUsername(username);
    user.setEmail(username + "@example.com");
    user.setPassword("password");
    return userRepository.save(user);
  }

  private PaperSubmissionDraft createDraft(User owner, String title) {
    PaperSubmissionDraft draft = new PaperSubmissionDraft();
    draft.setOwner(owner);
    draft.setManuscriptType("Research Article");
    draft.setFormDataJson("{\"title\":\"" + title + "\"}");
    draft.setCurrentSection("details");
    return draftRepository.saveAndFlush(draft);
  }

  private PaperSubmissionFile createSubmissionFile(
    PaperSubmissionDraft draft,
    String fileName,
    int sortOrder
  ) {
    PaperSubmissionFile file = new PaperSubmissionFile();
    file.setDraft(draft);
    file.setOriginalFileName(fileName);
    file.setDisplayName(fileName);
    file.setContentType("application/vnd.openxmlformats-officedocument.wordprocessingml.document");
    file.setFileSize(1024L);
    file.setRole(PaperFileRole.MANUSCRIPT);
    file.setDescription("Primary manuscript");
    file.setVisibility(PaperFileVisibility.PRIVATE);
    file.setStorageKey("drafts/" + draft.getId() + "/" + fileName);
    file.setUploadStatus(PaperUploadStatus.UPLOADED);
    file.setSortOrder(sortOrder);
    return file;
  }

  private PaperProfile createPaper(User owner, String title) {
    Category category = new Category();
    category.setName(title + " Category");
    category.setIcon("file-text");
    category.setDescription(title + " category");
    category = categoryRepository.save(category);

    Post post = new Post();
    post.setTitle(title);
    post.setContent("Paper content");
    post.setAuthor(owner);
    post.setCategory(category);
    post.setType(PostType.PAPER);
    post = postRepository.save(post);

    PaperProfile paper = new PaperProfile();
    paper.setPost(post);
    paper.setTitle(title);
    paper.setAbstractText("Abstract");
    paper.setSubjectArea("Computer Science");
    paper.setPreprintStatement("Previously posted as a preprint.");
    paper.setAiUseDisclosure("AI assisted language editing.");
    paper.setPrivateComments("For platform staff only.");
    paper.setAllAuthorsConsent(true);
    paper.setOriginalityConfirmed(true);
    paper.setRightsConfirmed(true);
    paper.setCorrespondingAuthorContactConfirmed(true);
    paper.setCorrespondingAuthorContactConfirmedAt(LocalDateTime.of(2026, 7, 12, 12, 0));
    paper.setCorrespondingAuthorContactConfirmedBy(owner);
    paper.setCreatedBy(owner);
    return paperProfileRepository.save(paper);
  }

  private PaperAuthor createAuthor(PaperProfile paper, Institution institution) {
    PaperAuthor author = new PaperAuthor();
    author.setPaper(paper);
    author.setDisplayName("Ada Lovelace");
    author.setGivenName("Ada");
    author.setMiddleName("Byron");
    author.setFamilyName("Lovelace");
    author.setAuthorRole("Author");
    author.setInstitution(institution);
    author.setAuthorOrder(1);
    return paperAuthorRepository.save(author);
  }

  private Institution createInstitution(String name) {
    Institution institution = new Institution();
    institution.setName(name);
    return institutionRepository.save(institution);
  }

  private PaperAuthorAffiliation createAffiliation(
    PaperAuthor author,
    Institution institution,
    String organizationName,
    boolean primary,
    int displayOrder
  ) {
    PaperAuthorAffiliation affiliation = new PaperAuthorAffiliation();
    affiliation.setPaperAuthor(author);
    affiliation.setInstitution(institution);
    affiliation.setOrganizationName(organizationName);
    affiliation.setDepartment("Department of Computing");
    affiliation.setAddressLines("1 Research Way");
    affiliation.setCountry("United Kingdom");
    affiliation.setRegion("London");
    affiliation.setCity("London");
    affiliation.setPostalCode("SW1A 1AA");
    affiliation.setPrimaryAffiliation(primary);
    affiliation.setDisplayOrder(displayOrder);
    return affiliation;
  }

  private PaperFundingRecord createFundingRecord(
    PaperProfile paper,
    String funderName,
    int displayOrder
  ) {
    PaperFundingRecord record = new PaperFundingRecord();
    record.setPaper(paper);
    record.setFunderName(funderName);
    record.setGrantId("GRANT-" + displayOrder);
    record.setDisplayOrder(displayOrder);
    return record;
  }

  private PaperFile createPaperFile(PaperProfile paper, String fileName, int sortOrder) {
    PaperFile file = new PaperFile();
    file.setPaper(paper);
    file.setOriginalFileName(fileName);
    file.setDisplayName(fileName);
    file.setContentType("application/pdf");
    file.setFileSize(2048L);
    file.setRole(PaperFileRole.PDF_VERSION);
    file.setDescription("Rendered paper PDF");
    file.setVisibility(PaperFileVisibility.PUBLIC);
    file.setStorageKey("papers/" + paper.getId() + "/" + fileName);
    file.setUploadStatus(PaperUploadStatus.UPLOADED);
    file.setSortOrder(sortOrder);
    return file;
  }
}
