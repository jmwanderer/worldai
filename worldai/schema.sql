DROP TABLE IF EXISTS elements;

CREATE TABLE elements (
  id INTEGER PRIMARY KEY,
  type INTEGER,    
  parent_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  properties TEXT NOT NULL
);      

CREATE TABLE images (
  id INTEGER PRIMARY KEY,
  filename TEXT NOT NULL
);

CREATE TABLE token_usage (
  world_id INTEGER NOT NULL,
  prompt_tokens INTEGER NOT NULL,
  complete_tokens INTEGER NOT NULL,
  total_tokens INTEGER NOT NULL
);


