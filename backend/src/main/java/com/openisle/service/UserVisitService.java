package com.openisle.service;

import com.openisle.config.CachingConfig;
import com.openisle.model.User;
import com.openisle.model.UserVisit;
import com.openisle.repository.UserRepository;
import com.openisle.repository.UserVisitRepository;
import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import lombok.RequiredArgsConstructor;
import org.springframework.cache.annotation.CacheConfig;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

@Service
@RequiredArgsConstructor
public class UserVisitService {

  private final UserVisitRepository userVisitRepository;
  private final UserRepository userRepository;

  private final RedisTemplate redisTemplate;

  public boolean recordVisit(String username) {
    User user = userRepository
      .findByUsername(username)
      .orElseThrow(() -> new com.openisle.exception.NotFoundException("User not found"));
    LocalDate today = LocalDate.now();
    return userVisitRepository
      .findByUserAndVisitDate(user, today)
      .map(v -> false)
      .orElseGet(() -> {
        UserVisit visit = new UserVisit();
        visit.setUser(user);
        visit.setVisitDate(today);
        userVisitRepository.save(visit);
        return true;
      });
  }

  /**
   * 统计访问次数，改为从缓存获取/数据库获取
   * @param username
   * @return
   */
  public long countVisits(String username) {
    User user = userRepository
      .findByUsername(username)
      .orElseThrow(() -> new com.openisle.exception.NotFoundException("User not found"));
    return countVisits(user);
  }

  public long countVisits(User user) {
    String username = user.getUsername();
    // 如果缓存存在就返回
    String key1 = CachingConfig.VISIT_CACHE_NAME + ":" + LocalDate.now() + ":count:" + username;
    Integer cached = (Integer) redisTemplate.opsForValue().get(key1);
    if (cached != null) {
      return cached.longValue();
    }

    // Redis Set 检查今天是否访问
    String todayKey = CachingConfig.VISIT_CACHE_NAME + ":" + LocalDate.now();
    boolean todayVisited = redisTemplate.opsForSet().isMember(todayKey, username);

    Long visitCount = userVisitRepository.countByUser(user);
    if (todayVisited) visitCount += 1;

    LocalDateTime now = LocalDateTime.now();
    LocalDateTime endOfDay = now.toLocalDate().atTime(23, 59, 59);
    long secondsUntilEndOfDay = Duration.between(now, endOfDay).getSeconds();

    // 写入缓存，设置 TTL，当天剩余时间
    redisTemplate.opsForValue().set(key1, visitCount, Duration.ofSeconds(secondsUntilEndOfDay));
    return visitCount;
  }

  public long countDau(LocalDate date) {
    LocalDate d = date != null ? date : LocalDate.now();
    return userVisitRepository.countByVisitDate(d);
  }

  public Map<LocalDate, Long> countDauRange(LocalDate start, LocalDate end) {
    Map<LocalDate, Long> result = new LinkedHashMap<>();
    if (start == null || end == null || start.isAfter(end)) {
      return result;
    }
    var list = userVisitRepository.countRange(start, end);
    for (var obj : list) {
      LocalDate d = (LocalDate) obj[0];
      Long c = (Long) obj[1];
      result.put(d, c);
    }
    // fill zero counts for missing dates
    for (LocalDate d = start; !d.isAfter(end); d = d.plusDays(1)) {
      result.putIfAbsent(d, 0L);
    }
    return result;
  }
}
