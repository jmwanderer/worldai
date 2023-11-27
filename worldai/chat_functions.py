import json
import os
import sqlite3
from . import elements



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

def debug_set_db(db):
  global my_db
  my_db = db

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


def track_tokens(world_id, prompt_tokens, complete_tokens, total_tokens):
  db = get_db()
  q = db.execute("SELECT COUNT(*) FROM token_usage WHERE world_id = ?",
                 (world_id,))
  if q.fetchone()[0] == 0:
    db.execute("INSERT INTO token_usage VALUES (?, 0, 0, 0)", (world_id,))
    
  db.execute("UPDATE token_usage SET prompt_tokens = prompt_tokens + ?, " +
             "complete_tokens = complete_tokens + ?, " +
             "total_tokens = total_tokens + ? WHERE world_id = ?",
             (prompt_tokens, complete_tokens, total_tokens, world_id))
  db.commit()

def dump_token_usage():
  db = get_db()
  q = db.execute("SELECT world_id, prompt_tokens, complete_tokens, "+
                 "total_tokens FROM token_usage")
  for (world_id, prompt_tokens, complete_tokens, total_tokens) in q.fetchall():
    print(f"id({world_id}): prompt: {prompt_tokens}, complete: " +
          f"{complete_tokens}, total: {total_tokens}")

  print()    
  q = db.execute("SELECT SUM(prompt_tokens), SUM(complete_tokens), "+
                 "SUM(total_tokens) FROM token_usage")
  (prompt_tokens, complete_tokens, total_tokens) = q.fetchone()
  print(f"total: prompt: {prompt_tokens}, complete: " +
        f"{complete_tokens}, total: {total_tokens}")
  
    
STATE_START = 1
STATE_EDIT_WORLD = 2

states = {
  STATE_START: [ "list_worlds", "read_world", "create_world" ],
  STATE_EDIT_WORLD: [ "update_world", "close_world" ]
  }

current_state = STATE_START

def get_available_functions():
  print(f"get available functions current state: {current_state}")
  return get_available_functions_for_state(current_state)

def get_available_functions_for_state(state):
  functions = {}
  for function in all_functions:
    functions[function["name"]] = function
  result = []
  for name in states[state]:
    result.append(functions[name])
  return result

def execute_function_call(function_call):
  global current_state
  
  arguments = json.loads(function_call['arguments'])  
  if function_call["name"] == "create_world":
    world = elements.World()
    world.setName(arguments["name"])
    world = elements.createWorld(get_db(), world)
    current_state = STATE_EDIT_WORLD
    return f"{world.id}"

  if function_call["name"] == "list_worlds":
    worlds = elements.listWorlds(get_db())
    return json.dumps(worlds)

  if function_call["name"] == "update_world":
    world = elements.loadWorld(get_db(), int(arguments["world_id"]))
    world.updateProperties(arguments)
    elements.updateWorld(get_db(), world)
    return ""

  if function_call["name"] == "read_world":
    world = elements.loadWorld(get_db(), int(arguments["world_id"]))
    content = { "world_id": world.id,
                **world.getProperties() }
    current_state = STATE_EDIT_WORLD    
    return json.dumps(content)

  if function_call["name"] == "close_world":
    current_state = STATE_START
    return ""

  return ""


all_functions = [
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

    {
      "name": "close_world",
      "description": "Done editing a world.",
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
    },
]            

