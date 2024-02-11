DROP TABLE IF EXISTS elements;
DROP TABLE IF EXISTS images;
DROP TABLE IF EXISTS token_usage;
DROP TABLE IF EXISTS threads;
DROP TABLE IF EXISTS character_threads;
DROP TABLE IF EXISTS world_state;

CREATE TABLE elements (
  id TEXT PRIMARY KEY,
  type INTEGER,    
  parent_id TEXT,
  name TEXT NOT NULL,
  properties TEXT NOT NULL,
  is_hidden BOOLEAN DEFAULT FALSE
);      

CREATE TABLE images (
  id TEXT PRIMARY KEY,
  parent_id TEXT NOT NULL,
  prompt TEXT NOT NULL,
  filename TEXT NOT NULL,
  is_hidden BOOLEAN DEFAULT FALSE
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
  thread TEXT
);

CREATE TABLE world_state (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  world_id TEXT NOT NULL,
  created INTEGER NOT NULL,
  updated INTEGER NOT NULL,
  state TEXT NOT NULL,
  FOREIGN KEY (world_id) REFERENCES elements(id)
);
 
CREATE TABLE character_threads (
  character_id TEXT NOT NULL,
  thread_id TEXT NOT NULL,
  world_state_id TEXT NOT NULL,
  PRIMARY KEY (world_state_id, character_id),
  FOREIGN KEY (world_state_id) REFERENCES world_state(id),
  FOREIGN KEY (character_id) REFERENCES elements(id),
  FOREIGN KEY (thread_id) REFERENCES threads(id)
);

CREATE TABLE info_docs (
  id TEXT NOT NULL,
  world_id TEXT NOT NULL,  
  owner_id TEXT NULL,
  wstate_id TEXT NULL,
  content TEXT NOT NULL,
  PRIMARY KEY (id),
  FOREIGN KEY (world_id) REFERENCES elements(id),
  FOREIGN KEY (wstate_id) REFERENCES world_state(id),
  FOREIGN KEY (owner_id) REFERENCES elements(id)
);

CREATE TABLE info_chunks(
  id TEXT NOT NULL,
  doc_id TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding TEXT,
  PRIMARY KEY (id),
  FOREIGN KEY (doc_id) REFERENCES info_docs(id)
);
  
CREATE TABLE element_info(
  element_id TEXT NOT NULL,
  info_index INTEGER DEFAULT 0,
  doc_id TEXT NOT NULL,
  PRIMARY KEY (element_id, info_index),
  FOREIGN KEY (element_id) REFERENCES elements(id),
  FOREIGN KEY (doc_id) REFERENCES info_docs(id)
);
