package com.openisle.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openisle.model.User;
import com.openisle.repository.UserRepository;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.password.PasswordEncoder;

class LiteratureDemoSeedServiceTest {

  @Test
  void seedsTwelveUsersAndTenRatingsForEachOfFivePapersIdempotently() {
    UserRepository users = mock(UserRepository.class);
    LiteratureRatingService ratings = mock(LiteratureRatingService.class);
    PasswordEncoder encoder = mock(PasswordEncoder.class);
    Map<String, User> stored = new HashMap<>();
    AtomicLong ids = new AtomicLong(100);
    when(encoder.encode(anyString())).thenReturn("encoded");
    when(users.findByUsername(anyString())).thenAnswer(call -> Optional.ofNullable(stored.get(call.getArgument(0))));
    when(users.save(any(User.class))).thenAnswer(call -> {
      User user = call.getArgument(0);
      user.setId(ids.incrementAndGet());
      stored.put(user.getUsername(), user);
      return user;
    });

    LiteratureDemoSeedService service = new LiteratureDemoSeedService(users, encoder, ratings);
    List<Long> paperIds = List.of(11L, 12L, 13L, 14L, 15L);

    LiteratureDemoSeedService.SeedResult first = service.seed(paperIds);
    LiteratureDemoSeedService.SeedResult second = service.seed(paperIds);

    assertEquals(12, first.usersAvailable());
    assertEquals(5, first.papersRated());
    assertEquals(50, first.ratingsWritten());
    assertEquals(12, stored.size());
    assertEquals(12, second.usersAvailable());
    verify(users, times(12)).save(any(User.class));
    verify(ratings, times(100)).rateLiterature(anyString(), anyLong(), any());
  }
}
