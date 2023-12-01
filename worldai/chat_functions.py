import json
import os
import sqlite3
import openai
import requests
import logging
from tenacity import retry, wait_random_exponential, stop_after_attempt

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
  
    
STATE_WORLDS = "State_Worlds"
STATE_VIEW_WORLD = "State_View_World"
STATE_EDIT_WORLD = "State_Edit_World"
STATE_EDIT_CHARACTERS = "State_Edit_Characters"

states = {
  STATE_WORLDS: [ "ListWorlds", "ReadWorld", "CreateWorld" ],
  STATE_VIEW_WORLD: [ "ReadWorld", "ChangeState"],
  STATE_EDIT_WORLD: [ "UpdateWorld", "ReadWorld",
                      "CreateWorldImage", "ChangeState" ],
  STATE_EDIT_CHARACTERS: [ "ListCharacters", "ReadCharacter",
                           "CreateCharacter", "UpdateCharacter",
                           "CreateCharacterImage", "ChangeState" ]
  }

instructions = {
  STATE_WORLDS:
"""
You can create a new world or resume work on an existing one by reading it.
Get a list of worlds before reading a world or creating a new one
To get a list of worlds, call ListWorlds
Before creating a new world, check if it already exists by using ListWorlds
""",

  STATE_VIEW_WORLD:
"""
We are viewing the world "{current_world_name}"

A world has a description and details that describe the nature of the world
and provide information.

To change information about the world, call change state to State_Edit_World.

A world has main characters that we develop and design.

To work on defining characters, change state to State_Edit_Characters.
""",
  
  STATE_EDIT_WORLD:
  """
We are working on the world "{current_world_name}"
  
A world needs a short high level description refelcting the nature of the world.

A world has details, that give more information about the world, the backstory, and includes a list of main characters, key sites, and special items.

You can create an image for the world with CreateWorldImage, using information from the description and details to create a prompt. Use a large prompt for the image.
  
Save information about the world by calling UpdateWorld

To work on characters call ChangeState
  """,

  STATE_EDIT_CHARACTERS:
"""
We are working on world "{current_world_name}"

Worlds have chacaters which are actors in the world with a backstory, abilities, and motivations.  You can create characters and change information about the characters.

You can update the name, description, and details of the character.
You save changes to a character by calling UpdateCharacter.  

Use information in the world details to guide character creation and design.

Before creating a new character, check if it already exists by calling the ListCharacters function.

You can create an image for the character with CreateCharacterImage, using information from the character description and detailed to create a prompt. Use a large prompt for the image.

Save detailed information about the character in character details.

To work on information about the world call ChangeState
""",
  }

  
def get_state_instructions():
  value = instructions[current_state].format(current_world_name = current_world_name)
  return value


current_state = STATE_WORLDS
current_world_name = None
current_world_id = None
current_character_name = None
current_character_id = None

def InitializeStateVars():
  global current_state
  global current_world_name
  global current_world_id
  global current_character_name
  global current_character_id

  current_state = STATE_WORLDS
  current_world_name = None
  current_world_id = None
  current_character_name = None
  current_character_id = None


  
def get_available_tools():
  return get_available_tools_for_state(current_state)

def get_available_tools_for_state(state):
  functions = {}
  for function in all_functions:
    functions[function["name"]] = function

  result = []
  for name in states[state]:
    tool = { "type": "function",
             "function": functions[name] }   
    result.append(tool)
  return result


def checkDuplication(name, element_list):
  """
  Check for any collisions between name and existing list
  element_list: list returned from getElements

  Return None if no conflict
  Return an id if a conflict

  """
  # Check if name is a substring of any existing name
  name = name.lower()
  for element in element_list:
    if name in element[elements.PROP_NAME].lower():
      return element[elements.PROP_ID]

  # Check if any existing name is a substring of the new name
  for element in element_list:
    if element[elements.PROP_NAME].lower() in name:
      return element[elements.PROP_ID]

  return None


# TODO - refactor into primary interface, display, and individual functions
def execute_function_call(function_name, arguments):
  global current_state
  global current_world_id
  global current_world_name
  global current_character_id  
  global current_character_name

  
  if function_name == "CreateWorld":
    world = elements.World()
    world.setName(arguments["name"])
    world.updateProperties(arguments)

    # Check for duplicates
    worlds = elements.listWorlds(get_db())    
    name = checkDuplication(world.getName(), worlds)
    if name is not None:
      content = { "error": f"Similar name already exists: {name}" }
      return json.dumps(content)
    
    world = elements.createWorld(get_db(), world)
    current_state = STATE_EDIT_WORLD
    current_world_id = world.id
    current_world_name = world.getName()
    return f'"{world.id}"'

  if function_name == "ListWorlds":
    worlds = elements.listWorlds(get_db())
    return json.dumps(worlds)

  if function_name == "UpdateWorld":
    world = elements.loadWorld(get_db(), current_world_id)
    world.updateProperties(arguments)
    elements.updateWorld(get_db(), world)

  if function_name == "ReadWorld":
    id = arguments["id"]
    world = elements.loadWorld(get_db(), id)
    if world is not None:
      content = { "id": world.id,
                  **world.getProperties() }
      if current_state == STATE_WORLDS:
        current_state = STATE_VIEW_WORLD
      current_world_id = world.id
      current_world_name = world.getName()
    else:
      content = { "error": f"no world {id}" }
    return json.dumps(content)

  if function_name == "ChangeState":
    state = arguments["state"]
    if states.get(state) is not None:
      # Check is state is legal
      if ((state == STATE_VIEW_WORLD or state == STATE_EDIT_WORLD or
           state == STATE_EDIT_CHARACTERS) and current_world_id is None):
        return "Error: must read or create a world"
      current_state = state

      if state != STATE_EDIT_CHARACTERS:
        current_character_id = None
        current_character_name = None
      if state == STATE_WORLDS:
        current_world_id = None
        current_world_name = None
      return "state changed"
    return "Error: unknown state"

  if function_name == "ListCharacters":
    characters = elements.listCharacters(get_db(), current_world_id)
    return json.dumps(characters)

  if function_name == "ReadCharacter":
    id = arguments["id"]
    character = elements.loadCharacter(get_db(), id)
    if character is not None:
      content = { "id": character.id,
                  **character.getProperties() }
      current_state = STATE_EDIT_CHARACTERS
      current_character_id  = character.id
      current_character_name = character.getName()      
    else:
      content = { "error": f"no character {id}" }
    return json.dumps(content)
  
  if function_name == "CreateCharacter":
    character = elements.Character(current_world_id)
    character.setName(arguments["name"])

    characters = elements.listCharacters(get_db(), current_world_id)    
    name = checkDuplication(character.getName(), characters)
    if name is not None:
      content = { "error": f"Similar name already exists: {name}" }
      return json.dumps(content)
    
    character.updateProperties(arguments)    
    character = elements.createCharacter(get_db(), character )
    current_character_id  = character.id
    current_character_name = character.getName()    
    current_state = STATE_EDIT_CHARACTERS   
    return f'"{character.id}"'

  if function_name == "UpdateCharacter":
    character = elements.loadCharacter(get_db(), current_character_id)
    if character is None:
      content = { "error": f"Character not found" }
      return json.dumps(content)
    character.updateProperties(arguments)
    elements.updateCharacter(get_db(), character)
    return "updated"
  
  if (function_name == "CreateWorldImage" or
      function_name == "CreateCharacterImage"):
    image = elements.Image()
    image.setPrompt(arguments["prompt"])
    logging.info("Create image: prompt %s", image.prompt)
    if current_state == STATE_EDIT_CHARACTERS:
      id = arguments["id"]
      character = elements.loadCharacter(get_db(), id)
      if character is None:
        return "error: no character %s" % id
      image.setParentId(id)
      current_character_id = id
      current_character_name = character.getName()
    else:
      image.setParentId(current_world_id)

    if image.parent_id is None:
      logging.info("create image error: empty parent_id")
      return "error"

    dest_file = os.path.join(DATA_DIR, image.getFilename())
    logging.info("dest file: %s", dest_file)
    if image_get_request(image.prompt, dest_file):
      logging.info("file create done, create image record")
      image = elements.createImage(get_db(), image)
      return "Image creation complete"
    return "error generating image"

  err_str = f"no such function: {name}"
  print(err_str)
  return '{ "error": "' + err_str + '" }'              


def image_get_request(prompt, dest_file):
  headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + openai.api_key,
  }
  json_data = {"model": "dall-e-3",
               "size" : "1024x1024",
               "prompt": prompt }
  try:
    print(f"post: {prompt}")
    response = requests.post(
      "https://api.openai.com/v1/images/generations",
      headers=headers,
      json=json_data,
      timeout=60,
    )
    result = response.json()
    print("image complete")
    if result.get("data") is None:
      return False
    
    response = requests.get(result["data"][0]["url"], stream=True)
    if response.status_code != 200:
      return False

    with open(dest_file, "wb") as f:
      response.raw.decode_content = True
      # Probably uses more memory than necessary
      f.write(response.raw.read())
    return True
      
  except Exception as e:
    print("Unable to generate ChatCompletion response")
    print(f"Exception: {e}")
    raise e



all_functions = [
  {
    "name": "ListWorlds",
    "description": "Get a list of existing worlds.",
    "parameters": {
      "type": "object",
      "properties": {
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
        "description": {
          "type": "string",
          "description": "Short high level description of the virtual world",
        },
      },
      "required": [ "name", "description" ]      
    },
  },


  {
    "name": "ReadWorld",
    "description": "Read in a specific virtual world.",
    "parameters": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "Unique identifier for world intance.",
        },
      },
      "required": [ "id"]
    },
  },
  
  
  {
    "name": "UpdateWorld",
    "description": "Update the values of the virtual world.",
    "parameters": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "Name of the virtual world.",
        },
        "description": {
          "type": "string",
          "description": "Short high level description of the world.",
        },
        "details": {
          "type": "string",
          "description": "Detailed information about the virtual world.",
        },
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
        "description": {
          "type": "string",
          "description": "Short description of the character",
        },
      },
      "required": [ "name", "description" ]
    },
  },

  {
    "name": "ReadCharacter",
    "description": "Read in a specific character.",
    "parameters": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "Unique identifier for the character.",
        },
      },
      "required": [ "id"]
    },
  },

  {
    "name": "ChangeState",
    "description": "Change the current state for a new activity.",
    "parameters": {
      "type": "object",
      "properties": {
        "state": {
          "type": "string",
          "description": "The new state",
        },
      },
    },
  },

  {
    "name": "UpdateCharacter",
    "description": "Update the values of the character.",
    "parameters": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "Name of the character.",
        },
        "description": {
          "type": "string",
          "description": "Short description of the character",
        },
        "details": {
          "type": "string",
          "description": "Detailed information about the character.",
        },
      },
    }
  },
  
  {
    "name": "CreateWorldImage",
    "description": "Create an image for the world",
    "parameters": {
      "type": "object",
      "properties": {
        "prompt": {
          "type": "string",
          "description": "A prompt from which to create the image.",
        },
      },
      "required": [ "prompt" ],
    },
  },

  {
    "name": "CreateCharacterImage",
    "description": "Create an image for a specific character",
    "parameters": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "Unique identifier for the character.",
        },
        "prompt": {
          "type": "string",
          "description": "A prompt from which to create the image.",
        },
      },
      "required": [ "id", "prompt" ],
    },
  },
]

