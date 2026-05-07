ALTER TABLE posts
  MODIFY COLUMN type ENUM('LOTTERY', 'NORMAL', 'PAPER', 'POLL', 'PROPOSAL') NOT NULL DEFAULT 'NORMAL';

UPDATE posts p
JOIN paper_profiles pp ON pp.post_id = p.id
SET p.type = 'PAPER'
WHERE p.type <> 'PAPER';
