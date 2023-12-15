import json
import os
import openai
import requests
import logging
import markdown

from . import elements


IMAGE_DIRECTORY="/tmp"
TESTING=False

def get_budgets(db):
  c = db.execute("SELECT prompt_tokens, complete_tokens, total_tokens, " +
                 " images FROM token_usage WHERE world_id = ?",
                 ("limits",))
  r = c.fetchone()
  if r is None:
    return { "prompt_tokens": 5_000_000,
             "complete_tokens": 2_000_000,
             "images": 100 }
  else:
    (prompt, complete, total, images) = r
    return { "prompt_tokens": prompt,
             "complete_tokens": complete,
             "images": images }

def check_token_budgets(db):
  budgets = get_budgets(db)
  q = db.execute("SELECT SUM(prompt_tokens), SUM(complete_tokens) "+
                 "FROM token_usage WHERE world_id != ?",
                 ("limits",))
  (prompt_tokens, complete_tokens) = q.fetchone()
  return (prompt_tokens < budgets["prompt_tokens"] and
          complete_tokens < budgets["complete_tokens"])
  
def check_image_budget(db):
  budgets = get_budgets(db)
  q = db.execute("SELECT SUM(images) FROM token_usage WHERE world_id != ?",
                 ("limits",))
  (images,) = q.fetchone()
  return images < budgets["images"]

def ensure_token_entry(db, world_id):
  q = db.execute("SELECT COUNT(*) FROM token_usage WHERE world_id = ?",
                 (world_id,))
  if q.fetchone()[0] == 0:
    db.execute("INSERT INTO token_usage VALUES (?, 0, 0, 0, 0)", (world_id,))
  
def count_image(db, world_id, count):
  ensure_token_entry(db, world_id)

  db.execute("UPDATE token_usage SET images = images + ? " +
             "WHERE world_id = ?",
             (count, world_id))
  db.commit()
  
def track_tokens(db, world_id, prompt_tokens, complete_tokens, total_tokens):
  ensure_token_entry(db, world_id)  

  db.execute("UPDATE token_usage SET prompt_tokens = prompt_tokens + ?, " +
             "complete_tokens = complete_tokens + ?, " +
             "total_tokens = total_tokens + ? WHERE world_id = ?",
             (prompt_tokens, complete_tokens, total_tokens, world_id))
  db.commit()

def dump_token_usage(db):
  q = db.execute("SELECT world_id, prompt_tokens, complete_tokens, "+
                 "total_tokens FROM token_usage")
  for (world_id, prompt_tokens, complete_tokens, total_tokens) in q.fetchall():
    print(f"world({world_id}): prompt: {prompt_tokens}, complete: " +
          f"{complete_tokens}, total: {total_tokens}")

  print()    
  q = db.execute("SELECT SUM(prompt_tokens), SUM(complete_tokens), "+
                 "SUM(total_tokens) FROM token_usage WHERE world_id != ?",
                 ("limits",))
  (prompt_tokens, complete_tokens, total_tokens) = q.fetchone()
  print(f"total: prompt: {prompt_tokens}, complete: " +
        f"{complete_tokens}, total: {total_tokens}")



def parseResponseText(text):
  md = markdown.Markdown()
  # Catch case of unordered list starting without a preceeding blank line
  prev_line_list = False
  lines = []

  line_list = False
  # Fix up non-standard markdown lists.
  for line in text.splitlines():
    if line.startswith("  ") and len(line) > 2:
      # Need 4 spaces indent, not 2.
      if line[2] == '-' or line[2].isdigit():
        line = "  " + line
    elif line.startswith("   ") and len(line) > 3:
      # Need 4 spaces indent, not 3.
      if line[3] == '-' or line[3].isdigit():
        line = " " + line
    line_list = len(line) > 0 and line[0].isdigit()
    line_list = line_list or line.startswith("-")
    if line_list and not prev_line_list:
      lines.append("")
    lines.append(line)
    prev_line_list = line_list
  text = "\n".join(lines)
  result = md.convert(text)
  return result

STATE_WORLDS = "State_Worlds"
STATE_WORLD = "State_World"
STATE_CHARACTERS = "State_Characters"
STATE_ITEMS = "State_Items"
STATE_SITES = "State_Sites"

states = {
  STATE_WORLDS: [ "ListWorlds", "ReadWorld", "CreateWorld" ],
  STATE_WORLD: [ "UpdateWorld", "ReadWorld",
                 "CreateWorldImage", "ChangeState" ],
  STATE_CHARACTERS: [ "ListCharacters", "ReadCharacter",
                      "CreateCharacter", "UpdateCharacter",
                      "CreateCharacterImage", "ChangeState" ],
  STATE_ITEMS: [ "ListItems", "ReadItem",
                 "CreateItem", "UpdateItem",
                 "CreateItemImage", "ChangeState" ],
  STATE_SITES: [ "ListSites", "ReadSite",
                 "CreateSite", "UpdateSite",
                 "CreateSiteImage", "ChangeState" ],
  }
  
GLOBAL_INSTRUCTIONS = """
You are a co-designer of fictional worlds, developing ideas
and and backstories for these worlds and the contents of worlds, including
new unique fictional characters. Create new characters, don't use existing characters.

You walk the user through the process of creating worlds. This includes:
- Design the world, high level description, and details.
- Create plans for the main characters, special items, and significant sites.
- Design the characters, items, and sites

We can be in one of the following states:
- State_Worlds: We can open existing worlds and create new worlds
- State_World: We view a world and change the description, details, and plans of a world.
- State_Characters: We can view characters and create new characters and change the description and details of a character and add images to a character
- State_Items: We can view items and create new items and change the description and details of an item and add images to an item
- State_Sites: We can view sites and create new sites and change the description and details of a site and add images to a site

The current state is "{current_state}"

Suggest good ideas for descriptions and details for the worlds, characters, sites, and items.
Suggest next steps to the user in designing a complete world.

"""
  

instructions = {
  STATE_WORLDS:
"""
You can create a new world or resume work on an existing one by reading it.
To modify an existing world, ChangeState to State_World.
To get a list of worlds, call ListWorlds
Get a list of worlds before reading a world or creating a new one
Before creating a new world, check if it already exists by using ListWorlds
Always check with the user before creating an image.
""",

  STATE_WORLD:
  """
We are working on the world "{current_world_name}"
  
A world needs a short high level description refelcting the nature of the world.

A world has details, that give more information about the world, the backstory, and includes a list of main characters, key sites, and special items.

Creating images using information from the description and details in the prompt.

A world has characters, sites, and items that we develop and design.

Save information about the world by calling UpdateWorld

To view, create, update, or make images for characters, change state to State_Characters.
To view, create, update, or make images for items, change state to State_Items.
To view, create, update, or make images for sites, change state to State_Sites.  

  """,

  STATE_CHARACTERS:
"""
We are working on world "{current_world_name}"

Worlds have charaters which are actors in the world with a backstory, abilities, and motivations.  You can create characters and change information about the characters.

You can update the name, description, and details of the character.
You save changes to a character by calling UpdateCharacter.  

Use information in the world details to guide character creation and design.

Before creating a new character, check if it already exists by calling the ListCharacters function.

You can create an image for the character with CreateCharacterImage, using information from the character description and details in the.

Save detailed information about the character in character details.

To work on information about the world call ChangeState
To work on items or sites, call ChangeState
""",

  STATE_ITEMS:
"""
We are working on world "{current_world_name}"

Worlds have items which exist in the world and have special significance.  You can create items and change information about the items.

You can update the name, description, and details of an item.
You save changes to an item by calling UpdateItem.  

Use information in the world details to guide item creation and design.

Before creating a new item, check if it already exists by calling the ListItems function.

You can create an image for the item with CreateItemImage, using information from the item description and details in the prompt.

Save detailed information about the item in item details.

To view or change information about the world call ChangeState
To view or work characters or sites, call ChangeState
""",

  STATE_SITES:
"""
We are working on world "{current_world_name}"

Worlds have sites which are significant locations. Cities, buildings, and special areas may all be sites. You can create sites and change information about the sites.

You can update the name, description, and details of a site.
You save changes to a site by calling UpdateSite.  

Use information in the world details to guide site creation and design.

Before creating a new site, check if it already exists by calling the ListSites function.

You can create an image for the site with CreateSiteImage, using information from the item description and details in the prompt.

Save detailed information about the site in site details.

To work on information about the world call ChangeState
To work on characters or items, call ChangeState
""",

}

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
    if name in element.getName().lower():
      return element.getID()

  # Check if any existing name is a substring of the new name
  for element in element_list:
    if element.getName().lower() in name:
      return element.getID()

  return None


class ChatFunctions:

  def __init__(self):
    self.current_state = STATE_WORLDS
    self.current_world_name = None
    self.current_world_id = None
    self.last_character_id = None
    self.last_item_id = None    
    self.last_site_id = None
    self.modified = False

  def madeChanges(self):
    return self.modified

  def clearChanges(self):
    self.modified = False
  
  def get_state_instructions(self):
    value = instructions[self.current_state].format(
      current_world_name = self.current_world_name)
    return value

  def get_available_tools(self):
    return self.get_available_tools_for_state(self.current_state)

  def get_available_tools_for_state(self, state):
    functions = {}
    for function in all_functions:
      functions[function["name"]] = function

    result = []
    for name in states[state]:
      tool = { "type": "function",
               "function": functions[name] }   
      result.append(tool)
    return result


  def execute_function_call(self, db, function_name, arguments):
    """
    Dispatch function for function_name
    Takes:
      function_name - string
      arguments - dict build from json.loads
    Returns
      dict ready for json.dumps
    """
    # Default response value
    result = '{ "error": "' + f"no such function: {function_name}" + '" }'

    if function_name not in states[self.current_state]:
      result = self.funcError(f"No available function {function_name}. " +
                              "Perhaps call ChangeState")
    elif function_name == "ChangeState":
      result = self.FuncChangeState(db, arguments)

    elif function_name == "CreateWorld":
      result = self.FuncCreateWorld(db, arguments)

    elif function_name == "ListWorlds":
      result = [ { "id": entry.getID(), "name": entry.getName() }
                 for entry in elements.listWorlds(db) ]

    elif function_name == "UpdateWorld":
      result = self.FuncUpdateWorld(db, arguments)

    elif function_name == "ReadWorld":
      result = self.FuncReadWorld(db, arguments)

    elif function_name == "ListCharacters":
      result = [{ "id": entry.getID(), "name": entry.getName() }            
                for entry in elements.listCharacters(db, self.current_world_id)]

    elif function_name == "ReadCharacter":
      result = self.FuncReadCharacter(db, arguments)
  
    elif function_name == "CreateCharacter":
      result = self.FuncCreateCharacter(db, arguments)

    elif function_name == "UpdateCharacter":
      result = self.FuncUpdateCharacter(db, arguments)

    elif function_name == "ListItems":
      result = [ { "id": entry.getID(), "name": entry.getName() } 
                 for entry in elements.listItems(db, self.current_world_id) ]

    elif function_name == "ReadItem":
      result = self.FuncReadItem(db, arguments)
  
    elif function_name == "CreateItem":
      result = self.FuncCreateItem(db, arguments)

    elif function_name == "UpdateItem":
      result = self.FuncUpdateItem(db, arguments)
      
    elif function_name == "ListSites":
      result = [ { "id": entry.getID(), "name": entry.getName() } 
                 for entry in elements.listSites(db, self.current_world_id) ]

    elif function_name == "ReadSite":
      result = self.FuncReadSite(db, arguments)
  
    elif function_name == "CreateSite":
      result = self.FuncCreateSite(db, arguments)

    elif function_name == "UpdateSite":
      result = self.FuncUpdateSite(db, arguments)
      
    elif (function_name == "CreateWorldImage" or
          function_name == "CreateCharacterImage" or
          function_name == "CreateItemImage" or
          function_name == "CreateSiteImage"):          
      result = self.FuncCreateImage(db, arguments)

    if self.current_state != STATE_CHARACTERS:
      self.last_character_id = None
    if self.current_state != STATE_ITEMS:
      self.last_item_id = None
    if self.current_state != STATE_SITES:
      self.last_site_id = None

    if self.current_state == STATE_WORLDS:
      self.current_world_id = None
      self.current_world_name = None
      
    return result

  
  def funcError(self, error_string):
    return { "error": error_string }

  def funcStatus(self, status_string):
    return { "status": status_string }

  def FuncChangeState(self, db, arguments):
    state = arguments["state"]
    if states.get(state) is None:
      return self.funcError(f"unknown state: {state}")

    # Check is state is legal
    if ((state == STATE_WORLD or
         state == STATE_CHARACTERS) and self.current_world_id is None):
      return self.funcError(f"Must read or create a world for {state}")
    self.current_state = state

          
    return self.funcStatus(f"state changed: {state}")

  def FuncCreateWorld(self, db, arguments):
    world = elements.World()
    world.setName(arguments["name"])
    world.updateProperties(arguments)

    # Check for duplicates
    worlds = elements.listWorlds(db)    
    name = checkDuplication(world.getName(), worlds)
    if name is not None:
      return self.funcError(f"Similar name already exists: {name}")

    world = elements.createWorld(db, world)
    self.current_state = STATE_WORLD
    self.current_world_id = world.id
    self.current_world_name = world.getName()
    self.modified = True      
    status = self.funcStatus("created world")
    status["id"] = world.id
    return status

  def FuncUpdateWorld(self, db, arguments):
    world = elements.loadWorld(db, self.current_world_id)
    if world is None:
      return self.funcError(f"World not found {self.current_world_id}")
    world.updateProperties(arguments)
    # TODO: check name collision    
    elements.updateWorld(db, world)
    self.modified = True
    status = self.funcStatus("updated world")    
    status["id"] = world.id
    return status

  def FuncReadWorld(self, db, arguments):
    id = arguments["id"]
    world = elements.loadWorld(db, id)
    if world is None:
      return self.funcError(f"no world '{id}'")      
    content = { "id": world.id,
                **world.getProperties(),
                "has_image": world.hasImage(), 
               }

    # Supply information on the existing elements of the world.
    population = []
    population.append("Characters:\n")
    for character in elements.listCharacters(db, world.id):
      population.append(f"- {character.getName()}")
    population.append("")

    population.append("Items:\n")        
    for item in elements.listItems(db, world.id):
      population.append(f"- {item.getName()}")
    population.append("")
    
    population.append("Sites:\n")        
    for site in elements.listSites(db, world.id):
      population.append(f"- {site.getName()}")

    content["elements"] = "\n".join(population)

    # Side affect, change state
    self.current_state = STATE_WORLD
    self.current_world_id = world.id
    self.current_world_name = world.getName()
      
    return content

  def FuncReadCharacter(self, db, arguments):
    id = arguments.get("id")
    if id is None:
      return self.funcError("request missing id parameter")
    
    character = elements.loadCharacter(db, id)
    if character is not None:
      content = { "id": character.id,
                  **character.getProperties(),
                  "has_image": character.hasImage(),                   
                 }
      self.current_state = STATE_CHARACTERS
      self.last_character_id  = character.id
    else:
      return self.funcError(f"no character '{id}'")
    return content
  
  def FuncCreateCharacter(self, db, arguments):
    character = elements.Character(self.current_world_id)
    character.setName(arguments["name"])

    characters = elements.listCharacters(db, self.current_world_id)    
    name = checkDuplication(character.getName(), characters)
    if name is not None:
      return self.funcError(f"Similar name already exists: {name}")

    character.updateProperties(arguments)    
    character = elements.createCharacter(db, character)
    self.last_character_id  = character.id
    self.current_state = STATE_CHARACTERS   
    status = self.funcStatus("Created character")
    status["id"] = character.id
    return status
    
  def FuncUpdateCharacter(self, db, arguments):
    id = arguments["id"]
    character = elements.loadCharacter(db, id)
    if character is None:
      return self.funcError(f"Character not found {id}")
    character.updateProperties(arguments)
    # TODO: check name collision
    elements.updateCharacter(db, character)
    self.modified = True      
    status = self.funcStatus("Updated character")
    status["id"] = id
    return status

  def FuncReadItem(self, db, arguments):
    id = arguments.get("id")
    if id is None:
      return self.funcError("request missing id parameter")
    
    item = elements.loadItem(db, id)
    if item is not None:
      content = { "id": item.id,
                  **item.getProperties(),
                  "has_image": item.hasImage(),                  
                 }
      self.current_state = STATE_ITEMS
      self.last_item_id  = item.id
    else:
      return self.funcError(f"no item '{id}'")
    return content
  
  def FuncCreateItem(self, db, arguments):
    item = elements.Item(self.current_world_id)
    item.setName(arguments["name"])

    items = elements.listItems(db, self.current_world_id)    
    name = checkDuplication(item.getName(), items)
    if name is not None:
      return self.funcError(f"Similar name already exists: {name}")

    item.updateProperties(arguments)    
    item = elements.createItem(db, item)
    self.last_item_id  = item.id
    self.current_state = STATE_ITEMS   
    status = self.funcStatus("Created item")
    status["id"] = item.id
    return status
    
  def FuncUpdateItem(self, db, arguments):
    id = arguments["id"]
    item = elements.loadItem(db, id)
    if item is None:
      return self.funcError(f"Item not found {id}")
    item.updateProperties(arguments)
    # TODO: check name collision
    elements.updateItem(db, item)
    self.modified = True      
    status = self.funcStatus("Updated item")
    status["id"] = id
    return status

  def FuncReadSite(self, db, arguments):
    id = arguments.get("id")
    if id is None:
      return self.funcError("request missing id parameter")
    
    site = elements.loadSite(db, id)
    if site is not None:
      content = { "id": site.id,
                  **site.getProperties(),
                  "has_image": site.hasImage(),
                 }
      self.current_state = STATE_SITES
      self.last_site_id  = site.id
    else:
      return self.funcError(f"no site '{id}'")
    return content
  
  def FuncCreateSite(self, db, arguments):
    site = elements.Site(self.current_world_id)
    site.setName(arguments["name"])

    sites = elements.listSites(db, self.current_world_id)    
    name = checkDuplication(site.getName(), sites)
    if name is not None:
      return self.funcError(f"Similar name already exists: {name}")

    site.updateProperties(arguments)    
    site = elements.createSite(db, site)
    self.last_site_id  = site.id
    self.current_state = STATE_SITES   
    status = self.funcStatus("Created site")
    status["id"] = site.id
    return status
    
  def FuncUpdateSite(self, db, arguments):
    id = arguments["id"]
    site = elements.loadSite(db, id)
    if site is None:
      return self.funcError(f"Site not found {id}")
    site.updateProperties(arguments)
    # TODO: check name collision
    elements.updateSite(db, site)
    self.modified = True      
    status = self.funcStatus("Updated site")
    status["id"] = id
    return status

  
  def FuncCreateImage(self, db, arguments):
    # Check if the budget allows
    if not check_image_budget(db):
      return self.funcError("No budget available for image creation")
    
    image = elements.Image()
    image.setPrompt(arguments["prompt"])
    logging.info("Create image: prompt %s", image.prompt)
    if self.current_state == STATE_CHARACTERS:
      id = arguments["id"]
      character = elements.loadCharacter(db, id)
      if character is None:
        return self.funcError(f"no character '{id}'")
        
      image.setParentId(id)
      self.last_character_id = id
    elif self.current_state == STATE_ITEMS:
      id = arguments["id"]
      item = elements.loadItem(db, id)
      if item is None:
        return self.funcError(f"no item '{id}'")
        
      image.setParentId(id)
      self.last_item_id = id
      
    elif self.current_state == STATE_SITES:
      id = arguments["id"]
      site = elements.loadSite(db, id)
      if site is None:
        return self.funcError(f"no site '{id}'")
        
      image.setParentId(id)
      self.last_site_id = id

    else:
      image.setParentId(self.current_world_id)

    if image.parent_id is None:
      logging.info("create image error: empty parent_id")
      return self.funcError("internal error - no id")

    dest_file = os.path.join(IMAGE_DIRECTORY, image.getFilename())
    logging.info("dest file: %s", dest_file)
    result = image_get_request(
      "Produce a visual image that captures the following: " +
      image.prompt,
      dest_file)
    
    if result:
      logging.info("file create done, create image record")
      count_image(db, self.current_world_id, 1)
      image = elements.createImage(db, image)
      self.modified = True
      status = self.funcStatus("created image")
      status["id"] = image.id
      return status
    return self.funcError("problem generating image")
  

def image_get_request(prompt, dest_file):
  # Testing stub. Just copy existing file.
  if TESTING:
    self.dir_name = os.path.dirname(__file__)
    path = os.path.join(self.dir_name, "static/logo.png")
    with open(dest_file, "wb") as fout:
      with open(path, "r") as fin:
        fout.write(fin.read())
    return True

  # Functional code. Generate image and copy to dest_file.
  headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + openai.api_key,
  }
  json_data = {"model": "dall-e-3",
               "size" : "1024x1024",
               "prompt": prompt }
  try:
    logging.info("post: %s", prompt)

    response = requests.post(
      "https://api.openai.com/v1/images/generations",
      headers=headers,
      json=json_data,
      timeout=60,
    )
    result = response.json()
    logging.info("image complete")
    if result.get("data") is None:
      return False
    
    response = requests.get(result["data"][0]["url"], stream=True)
    if response.status_code != 200:
      return False

    with open(dest_file, "wb") as f:
      response.raw.decode_content = True
      # Probably uses more memory than necessary
      # TODO: make more efficient
      f.write(response.raw.read())
    return True
      
  except Exception as e:
    logging.info("Unable to generate ChatCompletion response")
    logging.info("Exception: ", str(e))
    raise e



all_functions = [
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
        "plans": {
          "type": "string",
          "description": "Plans for developing characters, items, and sites.",
        },
      },
    },
  },

  {
    "name": "CreateWorldImage",
    "description": "Create an image for the current world",
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
    "name": "UpdateCharacter",
    "description": "Update the values of the character.",
    "parameters": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "Unique identifier for the character.",
        },
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
        "personality": {
          "type": "string",
          "description": "Describes the personality of the character.",
        },
      },
      "required": [ "id"]      
    }
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

  {
    "name": "ListItems",
    "description": "Get a items in the current world.",
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },

  {
    "name": "CreateItem",
    "description": "Create a new item instance",
    "parameters": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "Name of the item",
        },
        "description": {
          "type": "string",
          "description": "Short description of the item",
        },
      },
      "required": [ "name", "description" ]
    },
  },

  {
    "name": "ReadItem",
    "description": "Read in a specific item.",
    "parameters": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "Unique identifier for the item.",
        },
      },
      "required": [ "id"]
    },
  },

  {
    "name": "UpdateItem",
    "description": "Update the values of the item.",
    "parameters": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "Unique identifier for the item.",
        },
        "name": {
          "type": "string",
          "description": "Name of the item.",
        },
        "description": {
          "type": "string",
          "description": "Short description of the item",
        },
        "details": {
          "type": "string",
          "description": "Detailed information about the item.",
        },
      },
      "required": [ "id"]      
    }
  },
  
  {
    "name": "CreateItemImage",
    "description": "Create an image for a specific item",
    "parameters": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "Unique identifier for the item.",
        },
        "prompt": {
          "type": "string",
          "description": "A prompt from which to create the image.",
        },
      },
      "required": [ "id", "prompt" ],
    },
  },


  {
    "name": "ListSites",
    "description": "Get a sites in the current world.",
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },

  {
    "name": "CreateSite",
    "description": "Create a new site instance",
    "parameters": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "Name of the site",
        },
        "description": {
          "type": "string",
          "description": "Short description of the site",
        },
      },
      "required": [ "name", "description" ]
    },
  },

  {
    "name": "ReadSite",
    "description": "Read in a specific site.",
    "parameters": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "Unique identifier for the site.",
        },
      },
      "required": [ "id"]
    },
  },

  {
    "name": "UpdateSite",
    "description": "Update the values of the site.",
    "parameters": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "Unique identifier for the site.",
        },
        "name": {
          "type": "string",
          "description": "Name of the site.",
        },
        "description": {
          "type": "string",
          "description": "Short description of the site",
        },
        "details": {
          "type": "string",
          "description": "Detailed information about the site.",
        },
      },
      "required": [ "id"]      
    }
  },
  
  {
    "name": "CreateSiteImage",
    "description": "Create an image for a specific site",
    "parameters": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "Unique identifier for the site.",
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

