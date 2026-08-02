package com.openisle.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.openisle.dto.CommentInfoDto;
import com.openisle.dto.PostMetaDto;
import com.openisle.dto.UserDto;
import com.openisle.mapper.CategoryMapper;
import com.openisle.mapper.TagMapper;
import com.openisle.mapper.UserMapper;
import com.openisle.model.User;
import com.openisle.service.*;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(UserController.class)
@AutoConfigureMockMvc(addFilters = false)
class UserControllerTest {

  @Autowired
  private MockMvc mockMvc;

  @MockBean
  private ReactionService reactionService;

  @MockBean
  private SubscriptionService subscriptionService;

  @MockBean
  private UserService userService;

  @MockBean
  private ImageUploader imageUploader;

  @MockBean
  private PostService postService;

  @MockBean
  private CommentService commentService;

  @MockBean
  private LevelService levelService;

  @MockBean
  private TagService tagService;

  @MockBean
  private JwtService jwtService;

  @MockBean
  private UserMapper userMapper;

  @MockBean
  private TagMapper tagMapper;

  @MockBean
  private CategoryMapper categoryMapper;

  @Test
  void getCurrentUser() throws Exception {
    User u = new User();
    u.setId(1L);
    u.setUsername("alice");
    u.setEmail("a@b.com");
    u.setAvatar("http://x/avatar.png");
    Mockito.when(userService.findByUsername("alice")).thenReturn(Optional.of(u));
    UserDto dto = new UserDto();
    dto.setId(1L);
    dto.setUsername("alice");
    dto.setAvatar("http://x/avatar.png");
    Mockito.when(userMapper.toDto(eq(u), any())).thenReturn(dto);

    mockMvc
      .perform(
        get("/api/users/me").principal(new UsernamePasswordAuthenticationToken("alice", "p"))
      )
      .andExpect(status().isOk())
      .andExpect(jsonPath("$.avatar").value("http://x/avatar.png"));
  }

  @Test
  void uploadAvatar() throws Exception {
    MockMultipartFile file = new MockMultipartFile(
      "file",
      "a.png",
      MediaType.IMAGE_PNG_VALUE,
      "img".getBytes()
    );
    Mockito.when(imageUploader.upload(any(), eq("a.png"))).thenReturn(
      java.util.concurrent.CompletableFuture.completedFuture("http://img/a.png")
    );

    mockMvc
      .perform(
        multipart("/api/users/me/avatar")
          .file(file)
          .principal(new UsernamePasswordAuthenticationToken("alice", "p"))
      )
      .andExpect(status().isOk())
      .andExpect(jsonPath("$.url").value("http://img/a.png"));

    Mockito.verify(userService).updateAvatar("alice", "http://img/a.png");
  }

  @Test
  void uploadAvatarRejectsNonImage() throws Exception {
    MockMultipartFile file = new MockMultipartFile(
      "file",
      "a.txt",
      MediaType.TEXT_PLAIN_VALUE,
      "text".getBytes()
    );

    mockMvc
      .perform(
        multipart("/api/users/me/avatar")
          .file(file)
          .principal(new UsernamePasswordAuthenticationToken("alice", "p"))
      )
      .andExpect(status().isBadRequest())
      .andExpect(jsonPath("$.error").value("File is not an image"));

    Mockito.verify(imageUploader, Mockito.never()).upload(any(), any());
  }

  @Test
  void getUserByName() throws Exception {
    User u = new User();
    u.setId(2L);
    u.setUsername("bob");
    Mockito.when(userService.findByIdentifier("bob")).thenReturn(Optional.of(u));
    UserDto dto = new UserDto();
    dto.setId(2L);
    dto.setUsername("bob");
    Mockito.when(userMapper.toDto(eq(u), any())).thenReturn(dto);

    mockMvc
      .perform(get("/api/users/bob"))
      .andExpect(status().isOk())
      .andExpect(jsonPath("$.id").value(2));
  }

  @Test
  void listUserPosts() throws Exception {
    User user = new User();
    user.setUsername("bob");
    com.openisle.model.Category cat = new com.openisle.model.Category();
    cat.setName("tech");
    com.openisle.model.Post post = new com.openisle.model.Post();
    post.setId(3L);
    post.setTitle("hello");
    post.setCreatedAt(java.time.LocalDateTime.now());
    post.setCategory(cat);
    post.setAuthor(user);
    Mockito.when(userService.findByIdentifier("bob")).thenReturn(Optional.of(user));
    Mockito.when(postService.getRecentPostsByUser("bob", 10)).thenReturn(java.util.List.of(post));
    Mockito.when(userMapper.isPublicProfileContent(post)).thenReturn(true);
    PostMetaDto meta = new PostMetaDto();
    meta.setId(3L);
    meta.setTitle("hello");
    Mockito.when(userMapper.toMetaDto(post)).thenReturn(meta);

    mockMvc
      .perform(get("/api/users/bob/posts"))
      .andExpect(status().isOk())
      .andExpect(jsonPath("$[0].title").value("hello"));
  }

  @Test
  void listSubscribedPosts() throws Exception {
    User user = new User();
    user.setUsername("bob");
    com.openisle.model.Category cat = new com.openisle.model.Category();
    cat.setName("tech");
    com.openisle.model.Post post = new com.openisle.model.Post();
    post.setId(6L);
    post.setTitle("fav");
    post.setCreatedAt(java.time.LocalDateTime.now());
    post.setCategory(cat);
    post.setAuthor(user);
    Mockito.when(userService.findByIdentifier("bob")).thenReturn(Optional.of(user));
    Mockito.when(subscriptionService.getSubscribedPosts("bob")).thenReturn(java.util.List.of(post));
    Mockito.when(userMapper.isPublicProfileContent(post)).thenReturn(true);
    PostMetaDto meta = new PostMetaDto();
    meta.setId(6L);
    meta.setTitle("fav");
    Mockito.when(userMapper.toMetaDto(post)).thenReturn(meta);

    mockMvc
      .perform(get("/api/users/bob/subscribed-posts"))
      .andExpect(status().isOk())
      .andExpect(jsonPath("$[0].title").value("fav"));
  }

  @Test
  void listUserReplies() throws Exception {
    User user = new User();
    user.setUsername("bob");
    com.openisle.model.Post post = new com.openisle.model.Post();
    post.setId(5L);
    com.openisle.model.Category cat = new com.openisle.model.Category();
    cat.setName("tech");
    post.setCategory(cat);
    com.openisle.model.Comment comment = new com.openisle.model.Comment();
    comment.setId(4L);
    comment.setContent("hi");
    comment.setCreatedAt(java.time.LocalDateTime.now());
    comment.setAuthor(user);
    comment.setPost(post);
    Mockito.when(userService.findByIdentifier("bob")).thenReturn(Optional.of(user));
    Mockito.when(commentService.getRecentCommentsByUser("bob", 50)).thenReturn(
      java.util.List.of(comment)
    );
    Mockito.when(userMapper.isPublicProfileContent(post)).thenReturn(true);
    CommentInfoDto info = new CommentInfoDto();
    info.setId(4L);
    info.setContent("hi");
    Mockito.when(userMapper.toCommentInfoDto(comment)).thenReturn(info);

    mockMvc
      .perform(get("/api/users/bob/replies"))
      .andExpect(status().isOk())
      .andExpect(jsonPath("$[0].id").value(4));
  }

  @Test
  void aggregateUserData() throws Exception {
    User user = new User();
    user.setId(2L);
    user.setUsername("bob");
    user.setEmail("b@e.com");
    com.openisle.model.Category cat = new com.openisle.model.Category();
    cat.setName("tech");
    com.openisle.model.Post post = new com.openisle.model.Post();
    post.setId(3L);
    post.setTitle("hello");
    post.setCreatedAt(java.time.LocalDateTime.now());
    post.setCategory(cat);
    post.setAuthor(user);
    com.openisle.model.Comment comment = new com.openisle.model.Comment();
    comment.setId(4L);
    comment.setContent("hi");
    comment.setCreatedAt(java.time.LocalDateTime.now());
    comment.setAuthor(user);
    comment.setPost(post);

    Mockito.when(userService.findByIdentifier("bob")).thenReturn(Optional.of(user));
    Mockito.when(postService.getRecentPostsByUser("bob", 10)).thenReturn(java.util.List.of(post));
    Mockito.when(commentService.getRecentCommentsByUser("bob", 50)).thenReturn(
      java.util.List.of(comment)
    );
    Mockito.when(userMapper.isPublicProfileContent(post)).thenReturn(true);
    UserDto dtoAgg = new UserDto();
    dtoAgg.setId(2L);
    dtoAgg.setUsername("bob");
    Mockito.when(userMapper.toDto(eq(user), any())).thenReturn(dtoAgg);
    PostMetaDto metaAgg = new PostMetaDto();
    metaAgg.setId(3L);
    metaAgg.setTitle("hello");
    Mockito.when(userMapper.toMetaDto(post)).thenReturn(metaAgg);
    CommentInfoDto infoAgg = new CommentInfoDto();
    infoAgg.setId(4L);
    infoAgg.setContent("hi");
    Mockito.when(userMapper.toCommentInfoDto(comment)).thenReturn(infoAgg);

    mockMvc
      .perform(get("/api/users/bob/all"))
      .andExpect(status().isOk())
      .andExpect(jsonPath("$.user.id").value(2))
      .andExpect(jsonPath("$.posts[0].id").value(3))
      .andExpect(jsonPath("$.replies[0].id").value(4));
  }
}
