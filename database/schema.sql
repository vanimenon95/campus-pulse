-- Campus Pulse database schema (MySQL 8 / MariaDB 10.5+)
-- Usage:  mysql -u root -p < database/schema.sql
-- The Flask app can also create these tables itself (db.create_all) - this file documents the layout.

CREATE DATABASE IF NOT EXISTS campus_pulse CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE campus_pulse;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(160) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'student',      -- student | coordinator | admin
  department VARCHAR(120),
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME,
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS clubs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  category VARCHAR(40) NOT NULL DEFAULT 'Tech',
  description TEXT,
  coordinator_id INT,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME,
  FOREIGN KEY (coordinator_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS memberships (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  club_id INT NOT NULL,
  joined_at DATETIME,
  UNIQUE KEY uq_member (user_id, club_id),
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (club_id) REFERENCES clubs(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS club_activities (
  id INT AUTO_INCREMENT PRIMARY KEY,
  club_id INT NOT NULL,
  title VARCHAR(160) NOT NULL,
  body TEXT,
  created_at DATETIME,
  FOREIGN KEY (club_id) REFERENCES clubs(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS venues (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  location VARCHAR(160),
  capacity INT NOT NULL,
  facilities VARCHAR(255),
  open_time TIME NOT NULL,
  close_time TIME NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS venue_blackouts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  venue_id INT NOT NULL,
  start DATETIME NOT NULL,
  end DATETIME NOT NULL,
  reason VARCHAR(160),
  FOREIGN KEY (venue_id) REFERENCES venues(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS events (
  id INT AUTO_INCREMENT PRIMARY KEY,
  club_id INT NOT NULL,
  venue_id INT NOT NULL,
  title VARCHAR(160) NOT NULL,
  description TEXT,
  category VARCHAR(40) NOT NULL DEFAULT 'Tech',
  start DATETIME NOT NULL,
  end DATETIME NOT NULL,
  capacity INT,
  status VARCHAR(20) NOT NULL DEFAULT 'draft',      -- draft | published | cancelled
  created_by INT,
  created_at DATETIME,
  INDEX ix_events_start (start),
  FOREIGN KEY (club_id) REFERENCES clubs(id),
  FOREIGN KEY (venue_id) REFERENCES venues(id),
  FOREIGN KEY (created_by) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS registrations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  event_id INT NOT NULL,
  user_id INT NOT NULL,
  created_at DATETIME,
  attended TINYINT(1) NULL,                          -- NULL = not recorded yet
  marked_at DATETIME,
  UNIQUE KEY uq_registration (event_id, user_id),
  FOREIGN KEY (event_id) REFERENCES events(id),
  FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  kind VARCHAR(30),
  message VARCHAR(255) NOT NULL,
  event_id INT,
  is_read TINYINT(1) DEFAULT 0,
  created_at DATETIME,
  INDEX ix_notifications_user (user_id),
  FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS revoked_tokens (
  id INT AUTO_INCREMENT PRIMARY KEY,
  jti VARCHAR(64) NOT NULL UNIQUE,
  revoked_at DATETIME
) ENGINE=InnoDB;
