import json
import os
import sqlite3

functions = [
  {
    "name": "create_world",
    "description": "Create a new virtual world",
    "parameters": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "Name of the virtual world",
        },
        "description": {
          "type": "string",
          "description": "Describes the nature of the world",
        },
      },
    },
    "returns": {
      "type": "integer",
      "description": "Unique identifier for world instance.",
    },
  },
    {
      "name": "update_world",
      "description": "Update the values of the virtual world.",
      "parameters": {
        "type": "object",
        "properties": {
          "world_id": {
            "type": "integer",
            "description": "Unique identifier for world intance.",
          },
          "name": {
            "type": "string",
            "description": "Name of the virtual world.",
          },
          "description": {
            "type": "string",
            "description": "Describes the nature of the world.",
          },
          "details": {
            "type": "string",
            "description": "Detailed information about the virtual world.",
          },
        },
        "required": ["world_id"]
      },
      "returns": {
        "status" : {
          "type": "boolean",
          "description": "True for success",
        },
      },
    },
    {
      "name": "list_worlds",
      "description": "Get a list of available worlds.",
      "parameters": {
        "type": "object",
        "properties": {
        },
      },
      "returns": {
        "type": "object",
        "properties": {
          "world_id": {
            "type": "integer",
            "description": "Unique identifier for world intance.",
          },
          "name": {
            "type": "string",
            "description": "Name of the virtual world.",
          },
        },
      },
    },
    {
      "name": "read_world",
      "description": "Read in a specific virtual world.",
      "parameters": {
        "type": "object",
        "properties": {
          "world_id": {
            "type": "integer",
            "description": "Unique identifier for world intance.",
          },
        },
        "required": [ "world_id"]
      },
      "returns": {
        "type": "object",
        "properties": {
          "world_id": {
            "type": "integer",
            "description": "Unique identifier for world intance.",
          },
          "name": {
            "type": "string",
            "description": "Name of the virtual world.",
          },
          "description": {
            "type": "string",
            "description": "Describes the nature of the world.",
          },
          "details": {
            "type": "string",
            "description": "Detailed information about the virtual world.",
          },
        },
      },
    },  
]            



DATA_DIR = None
DATABASE = None

def init_config(data_dir, database):
  global DATA_DIR
  global DATABASE
  DATA_DIR = data_dir
  DATABASE = database
  check_init_db()
  
my_db = None
def get_db():
  global my_db
  if my_db is None:
    my_db = sqlite3.connect(
      os.path.join(DATA_DIR, DATABASE),
      detect_types=sqlite3.PARSE_DECLTYPES)
    my_db.row_factory = sqlite3.Row
  return my_db

def check_init_db():
  if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    
  if not os.path.exists(os.path.join(DATA_DIR, DATABASE)):
    path = os.path.join(os.path.dirname(__file__), "schema.sql")
    db = sqlite3.connect(os.path.join(DATA_DIR, DATABASE),
                              detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    with open(path) as f:
      db.executescript(f.read())
    db.close()

  

def execute_function_call(function_call):
  if function_call["name"] == "start_new_hangman_game":
    arguments = json.loads(function_call['arguments'])
    return "queen"

  if function_call["name"] == "record_guess":
  
    content = { "found" : False,
                "visible_word" : "__x++",
                "word" : "a new word",                
                "remaining_guesses" : 4,
                "status" : 1 }
    return json.dumps(content)

  return ""
