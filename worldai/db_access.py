import sqlite3
import os

DATABASE = None

def init_config(database):
  global DATABASE
  DATABASE = database
  check_init_db()
  
def open_db():
  db = sqlite3.connect(
    DATABASE)
    #detect_types=sqlite3.PARSE_DECLTYPES)
  #db.row_factory = sqlite3.Row
  return db

def check_init_db():
  data_dir = os.path.dirname(DATABASE)
  if not os.path.exists(data_dir):
    os.makedirs(data_dir)
    
  if not os.path.exists(DATABASE):
    path = os.path.join(os.path.dirname(__file__), "schema.sql")
    db = open_db()
    with open(path) as f:
      db.executescript(f.read())
    db.close()

