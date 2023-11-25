DROP TABLE IF EXISTS elements;

CREATE TABLE elements (
  id INTEGER PRIMARY KEY,
  parent_id INTEGER NOT NULL,  
  name TEXT NOT NULL,
  type INTEGER,
  description TEXT NOT NULL,
  details TEXT NOT NULL,
  properties TEXT NOT NULL
);      

