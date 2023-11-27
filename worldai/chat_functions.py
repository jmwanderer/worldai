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
    print(f"world({world_id}): prompt: {prompt_tokens}, complete: " +
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
  STATE_WORLDS: [ "ListWorlds", "ReadWorld", "CreateWorld" ],
  STATE_EDIT_WORLD: [ "UpdateWorld", "ReadWorld", "DoneWorld",
                      "OpenCharacters" ],
  STATE_CHARACTERS: [ "ListCharacters", "ReadCharacter",
                      "CreateCharacter", "DoneCharacters" ],
  STATE_EDIT_CHARACTER: [ "UpdateCharacter", "ReadCharacter",
                          "DoneCharacter" ],
  }

instructions = {
  STATE_WORLDS:
  """
  You can create a new world or resume work on an existing one by reading it.

  Before creating a new world, check if it already exists by calling the
  list_worlds function.
  
  To read an existing world, get the id from the list_worlds function.
  """,

  STATE_EDIT_WORLD:
  """
  A high level description of the world should include information such
  as the neture and characteristics of the world. Save the high level description of the world in description.

  We are working on world id {current_world_id}.

  The details of a world include a list of main characters, key sites,
  and special items.

  To create a new world or work on a different world, call DoneWorld.

  To develop details for the main characters, first call the OpenCharacters function.
  """,
                    
  STATE_CHARACTERS:
  """
  You can create new characters or read existing characters for further development of the character.

  Before creating a new character, check if it already exists by calling the
  ListCharacters function.

  We are working on world id {current_world_id}.

  Use information from the world details to guide character design.

  When done developing characters, return to designing the world by calling DoneCharacters.
  """,
                    
  STATE_EDIT_CHARACTER:
  """
    Characters are actors in the world with a backstory, abilities, and motivations.  You can save changes to a character by calling UpdateCharacter.

  Use information in the world details to guide character design.

  We are working on world id {current_world_id}.
  We are working on character id {current_character_id}.  

  Save detailed information about the character in character details.

  To work on other characters, call DoneCharacter
  """,
  }
  

current_state = STATE_WORLDS
current_world_id = 0
current_character_id = 0

def get_state_instructions():
  value = instructions[current_state]
  return value.format(current_world_id = current_world_id, 
                      current_character_id = current_character_id)

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
  global current_character_id  
  
  name = function_call["name"]
  arguments = function_call['arguments']
  arguments = json.loads(arguments)

  if function_call["name"] == "CreateWorld":
    world = elements.World()
    world.setName(arguments["name"])
    world = elements.createWorld(get_db(), world)
    current_state = STATE_EDIT_WORLD
    current_world_id = world.id
    return f"{world.id}"

  if function_call["name"] == "ListWorlds":
    worlds = elements.listWorlds(get_db())
    return json.dumps(worlds)

  if function_call["name"] == "UpdateWorld":
    world = elements.loadWorld(get_db(), int(arguments["world_id"]))
    world.updateProperties(arguments)
    elements.updateWorld(get_db(), world)
    return "updated"

  if function_call["name"] == "ReadWorld":
    id = int(arguments["world_id"])
    world = elements.loadWorld(get_db(), id)
    if world is not None:
      content = { "world_id": world.id,
                  **world.getProperties() }
      current_state = STATE_EDIT_WORLD
      current_world_id = world.id
    else:
      content = { "error": f"no world {id}" }
    return json.dumps(content)

  if function_call["name"] == "DoneWorld":
    current_state = STATE_WORLDS
    return "ok"

  if function_call["name"] == "OpenCharacters":
    current_state = STATE_CHARACTERS
    return "ok"

  if function_call["name"] == "ListCharacters":
    characters = elements.listCharacters(get_db(), current_world_id)
    return json.dumps(characters)

  if function_call["name"] == "ReadCharacter":
    id = int(arguments["id"])
    character = elements.loadCharacter(get_db(), id)
    if character is not None:
      content = { "id": character.id,
                  **character.getProperties() }
      current_state = STATE_EDIT_CHARACTER
      current_character_id  = character.id
    else:
      content = { "error": f"no character {id}" }
    return json.dumps(content)
  
  if function_call["name"] == "CreateCharacter":
    character = elements.Character(current_world_id)
    character.setName(arguments["name"])
    character = elements.createCharacter(get_db(), character )
    current_character_id  = character.id    
    current_state = STATE_EDIT_CHARACTER    
    return f"{character.id}"

  if function_call["name"] == "UpdateCharacter":
    character = elements.loadCharacter(get_db(), int(arguments["id"]))
    character.updateProperties(arguments)
    elements.updateCharacter(get_db(), character)
    return "updated"
  
  if function_call["name"] == "DoneCharacters":
    current_state = STATE_EDIT_WORLD
    return "ok"

  if function_call["name"] == "DoneCharacter":
    current_state = STATE_CHARACTERS
    current_character_id  = 0    
    return "ok"

  err_str = f"no such function: {name}"
  print(err_str)
  return '{ "error": "' + err_str + '" }'              


all_functions = [
  {
    "name": "ListWorlds",
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
    "name": "CreateWorld",
    "description": "Create a new virtual world",
    "parameters": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "Name of the virtual world",
        },
      },
      "required": [ "name" ]      
    },
    "returns": {
      "type": "integer",
      "description": "Unique identifier for world instance.",
    },
  },


  {
    "name": "ReadWorld",
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
    "name": "UpdateWorld",
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
    "name": "DoneWorld",
    "description": "Done editing a world.",
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },

  {
    "name": "OpenCharacters",
    "description": "Start working on characters.",
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },
  
  {
    "name": "ListCharacters",
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
    "name": "CreateCharacter",
    "description": "Create a new character instance",
    "parameters": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "Name of the character",
        },
      },
      "required": [ "name" ]
    },
    "returns": {
      "type": "integer",
      "description": "Unique identifier for world instance.",
    },
  },

  {
    "name": "ReadCharacter",
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
    "name": "DoneCharacters",
    "description": "Complete working on characters.",
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },

  {
    "name": "UpdateCharacter",
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
      "required": [ "id" ],
    }
  },
  
  {
    "name": "DoneCharacter",
    "description": "Complete working on a specifc character.",
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },

  {
    "name": "CreateImage",
    "description": "Create an image for a world, character, site, or item",
    "parameters": {
      "type": "object",
      "properties": {
        "prompt": {
          "type": "string",
          "description": "A prompt from which to create the image.",
        },
        "required": [ "prompt" ]        
      },        
      "returns": {
        "type": "object",
        "properties": {
          "id": {
            "type": "integer",
            "description": "Unique identifier for the image.",
          },
        },
      }
    },
  },
  
]

