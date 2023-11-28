DROP TABLE IF EXISTS elements;

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
  total_tokens INTEGER NOT NULL
);


