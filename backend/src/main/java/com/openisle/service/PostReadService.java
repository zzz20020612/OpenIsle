package com.openisle.service;

import com.openisle.model.Post;
import com.openisle.model.PostRead;
import com.openisle.model.User;
import com.openisle.repository.PostReadRepository;
import com.openisle.repository.PostRepository;
import com.openisle.repository.UserRepository;
import java.time.LocalDateTime;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class PostReadService {

  private final PostReadRepository postReadRepository;
  private final UserRepository userRepository;
  private final PostRepository postRepository;

  public void recordRead(String username, Long postId) {
    if (username == null) return;
    User user = userRepository
      .findByUsername(username)
      .orElseThrow(() -> new com.openisle.exception.NotFoundException("User not found"));
    Post post = postRepository
      .findById(postId)
      .orElseThrow(() -> new com.openisle.exception.NotFoundException("Post not found"));
    postReadRepository
      .findByUserAndPost(user, post)
      .ifPresentOrElse(
        pr -> {
          pr.setLastReadAt(LocalDateTime.now());
          postReadRepository.save(pr);
        },
        () -> {
          PostRead pr = new PostRead();
          pr.setUser(user);
          pr.setPost(post);
          pr.setLastReadAt(LocalDateTime.now());
          postReadRepository.save(pr);
        }
      );
  }

  public List<PostRead> getRecentReadsByUser(String username, int limit) {
    User user = userRepository
      .findByUsername(username)
      .orElseThrow(() -> new com.openisle.exception.NotFoundException("User not found"));
    Pageable pageable = PageRequest.of(0, limit);
    return postReadRepository.findByUserOrderByLastReadAtDesc(user, pageable);
  }

  public long countReads(String username) {
    User user = userRepository
      .findByUsername(username)
      .orElseThrow(() -> new com.openisle.exception.NotFoundException("User not found"));
    return countReads(user);
  }

  public long countReads(User user) {
    return postReadRepository.countByUser(user);
  }

  @org.springframework.transaction.annotation.Transactional
  public void deleteByPost(Post post) {
    postReadRepository.deleteByPost(post);
  }
}
