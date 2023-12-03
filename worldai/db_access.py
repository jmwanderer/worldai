import sqlite3
import os

DATA_DIR = None
DATABASE = None

def init_config(data_dir, database):
  global DATA_DIR
  global DATABASE
  DATA_DIR = data_dir
  DATABASE = database
  check_init_db()
  
def open_db():
  db = sqlite3.connect(
    os.path.join(DATA_DIR, DATABASE),
    detect_types=sqlite3.PARSE_DECLTYPES)
  db.row_factory = sqlite3.Row
  return db

def check_init_db():
  if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    
  if not os.path.exists(os.path.join(DATA_DIR, DATABASE)):
    path = os.path.join(os.path.dirname(__file__), "schema.sql")
    db = open_db()
    with open(path) as f:
      db.executescript(f.read())
    db.close()

