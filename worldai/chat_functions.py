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
  
    
STATE_WORLDS = 1
STATE_EDIT_WORLD = 2
STATE_CHARACTERS = 3
STATE_EDIT_CHARACTER = 4

states = {
  STATE_WORLDS: [ "list_worlds", "read_world", "create_world" ],
  STATE_EDIT_WORLD: [ "update_world", "read_world", "done_world",
                      "open_characters" ],
  STATE_CHARACTERS: [ "list_characters", "read_character",
                      "create_character", "done_characters" ],
  STATE_EDIT_CHARACTER: [ "update_character", "read_character",
                          "done_character" ],
  }

current_state = STATE_WORLDS
current_world_id = 0

def get_available_functions():
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
  global current_world_id
  
  name = function_call["name"]
  arguments = function_call['arguments']
  print(f'function call: {name}, arguments: {arguments}')
  arguments = json.loads(arguments)

  if function_call["name"] == "create_world":
    world = elements.World()
    world.setName(arguments["name"])
    world = elements.createWorld(get_db(), world)
    current_state = STATE_EDIT_WORLD
    current_world_id = world.id
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
    current_world_id = world.id    
    return json.dumps(content)

  if function_call["name"] == "done_world":
    current_state = STATE_WORLDS
    return ""

  if function_call["name"] == "open_characters":
    current_state = STATE_CHARACTERS
    return ""

  if function_call["name"] == "list_characters":
    worlds = elements.listCharacters(get_db())
    return json.dumps(worlds)

  if function_call["name"] == "read_character":
    character = elements.loadCharacter(get_db(), int(arguments["id"]))
    content = { "id": character.id,
                **character.getProperties() }
    current_state = STATE_EDIT_CHARACTER
    return json.dumps(content)
  
  if function_call["name"] == "create_character":
    character = elements.Character(current_world_id)
    character.setName(arguments["name"])
    world = elements.createCharacter(get_db(), character )
    current_state = STATE_EDIT_CHARACTER    
    return f"{world.id}"

  if function_call["name"] == "update_character":
    character = elements.loadCharacter(get_db(), int(arguments["id"]))
    character.updateProperties(arguments)
    elements.updateCharacter(get_db(), character)
    return ""
  
  if function_call["name"] == "done_characters":
    current_state = STATE_EDIT_WORLD
    return ""

  if function_call["name"] == "done_character":
    current_state = STATE_CHARACTERS
    return ""

  print(f"no such function: {name}")
  return ""


all_functions = [
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
    "name": "done_world",
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

  {
    "name": "open_characters",
    "description": "Start working on characters.",
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },
  
  {
    "name": "list_characters",
    "description": "Get a characters in the current world.",
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
    "returns": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "description": "Unique identifier for the character intance.",
        },
        "name": {
          "type": "string",
          "description": "Name of the character.",
        },
      },
    },
  },

  {
    "name": "create_character",
    "description": "Create a new character instance",
    "parameters": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "Name of the character",
        },
      },
    },
    "returns": {
      "type": "integer",
      "description": "Unique identifier for world instance.",
    },
  },

  {
    "name": "read_character",
    "description": "Read in a specific character.",
    "parameters": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "description": "Unique identifier for the character.",
        },
      },
      "required": [ "id"]
    },
    "returns": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "description": "Unique identifier for the character.",
        },
        "name": {
          "type": "string",
          "description": "Name of the character.",
        },
        "description": {
          "type": "string",
          "description": "Describes the character.",
        },
        "details": {
          "type": "string",
          "description": "Detailed information about the character.",
        },
      },
    },
  },

  {
    "name": "done_characters",
    "description": "Complete working on characters.",
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },

  {
    "name": "update_character",
    "description": "Update the values of the character.",
    "parameters": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "description": "Unique identifier for the character.",
        },
        "name": {
          "type": "string",
          "description": "Name of the character.",
        },
        "description": {
          "type": "string",
          "description": "Describes the nature the character.",
        },
        "details": {
          "type": "string",
          "description": "Detailed information about the character.",
        },
      },
      "required": ["id"]
    },
  },
  
  {
    "name": "done_character",
    "description": "Complete working on a specifc character.",
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },
]            

