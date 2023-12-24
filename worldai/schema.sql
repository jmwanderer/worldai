DROP TABLE IF EXISTS elements;
DROP TABLE IF EXISTS images;
DROP TABLE IF EXISTS token_usage;
DROP TABLE IF EXISTS threads;

CREATE TABLE elements (
  id TEXT PRIMARY KEY,
  type INTEGER,    
  parent_id TEXT,
  name TEXT NOT NULL,
  properties TEXT NOT NULL
);      

CREATE TABLE images (
  id TEXT PRIMARY KEY,
  parent_id TEXT NOT NULL,
  prompt TEXT NOT NULL,
  filename TEXT NOT NULL
);

CREATE TABLE token_usage (
  world_id STRING NOT NULL,
  prompt_tokens INTEGER NOT NULL,
  complete_tokens INTEGER NOT NULL,
  total_tokens INTEGER NOT NULL,
  images INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE threads (
  id TEXT PRIMARY KEY,
  created INTEGER NOT NULL,
  updated INTEGER NOT NULL,
  thread BLOB
);

CREATE TABLE character_threads (
  session_id TEXT NOT NULL,
  world_id TEXT NOT NULL,
  character_id TEXT NOT NULL,
  thread_id TEXT NOT NULL,
  PRIMARY KEY (session_id, world_id, character_id),
  FOREIGN KEY (thread_id) REFERENCES threads(id)
  FOREIGN KEY (world_id) REFERENCES elements(id)
  FOREIGN KEY (character_id) REFERENCES elements(id)    
);




