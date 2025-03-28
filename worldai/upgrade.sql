--
-- SQLite Schema
-- Upgrades DB to add ON DELETE CASCADE
-- Upgrades: 
--  commit d175cb83506cbd28696021c5a8b29565b8bee18a
--   to
--  commit 042e44d6278d5230d978eab4256f8880361dcaeb
--
--    Jim Wanderer
--    http://github.com/jmwanderer
--


PRAGMA foreign_keys=off;

ALTER TABLE world_state RENAME TO _world_state;

CREATE TABLE world_state (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  world_id TEXT NOT NULL,
  created INTEGER NOT NULL,
  updated INTEGER NOT NULL,
  state TEXT NOT NULL,
  FOREIGN KEY (world_id) REFERENCES elements(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
INSERT INTO world_state SELECT * FROM _world_state;
DROP TABLE _world_state;
 
ALTER TABLE character_threads RENAME TO _character_threads;

CREATE TABLE character_threads (
  character_id TEXT NOT NULL,
  thread_id TEXT NOT NULL,
  world_state_id TEXT NOT NULL,
  PRIMARY KEY (world_state_id, character_id),
  FOREIGN KEY (world_state_id) REFERENCES world_state(id) ON DELETE CASCADE,
  FOREIGN KEY (character_id) REFERENCES elements(id) ON DELETE CASCADE,
  FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
);
INSERT INTO character_threads SELECT * FROM _character_threads;
DROP TABLE _character_threads;
 
ALTER TABLE info_docs RENAME TO _info_docs;
CREATE TABLE info_docs (
  id TEXT NOT NULL,
  world_id TEXT NOT NULL,  
  owner_id TEXT NULL,
  wstate_id TEXT NULL,
  content TEXT NOT NULL,
  PRIMARY KEY (id),
  FOREIGN KEY (world_id) REFERENCES elements(id) ON DELETE CASCADE,
  FOREIGN KEY (wstate_id) REFERENCES world_state(id) ON DELETE CASCADE,
  FOREIGN KEY (owner_id) REFERENCES elements(id) ON DELETE CASCADE
);
INSERT INTO info_docs SELECT * FROM _info_docs;
DROP TABLE _info_docs;
 
ALTER TABLE info_chunks RENAME TO _info_chunks;
CREATE TABLE info_chunks(
  id TEXT NOT NULL,
  doc_id TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding TEXT,
  PRIMARY KEY (id),
  FOREIGN KEY (doc_id) REFERENCES info_docs(id) ON DELETE CASCADE
);
INSERT INTO info_chunks SELECT * FROM _info_chunks;
DROP TABLE _info_chunks;
 
ALTER TABLE element_info RENAME TO _element_info;
CREATE TABLE element_info(
  element_id TEXT NOT NULL,
  info_index INTEGER DEFAULT 0,
  doc_id TEXT NOT NULL,
  PRIMARY KEY (element_id, info_index),
  FOREIGN KEY (element_id) REFERENCES elements(id) ON DELETE CASCADE,
  FOREIGN KEY (doc_id) REFERENCES info_docs(id) ON DELETE CASCADE
);
INSERT INTO element_info SELECT * FROM _element_info;
DROP TABLE _element_info;
 
