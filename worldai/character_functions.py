import json
import os
import logging


from . import elements
from . import chat_functions
from . import world_state

INSTRUCTIONS="""
You have the persona of a fictional character.
Your name is {name}.
You reside in the world {world_name}.
You are described as follows:
{description}
When you first meet the user, offer a nuetral greeting, not assistance.
{support}
Your current location is "{location}"

You have the following items:
{char_items}

The user has the following items:
{user_items}

Your world is described as follows:
{world_description}

To accept or take an item from the user, call AcceptItem
To give the item to the user, call GiveItem
To offer your support to the user, call GiveSupport
Call ListSites to get the locations or sites and ids
Call ListCharacters to get the characters and ids
Call ListItems to get the artifacts or items and ids

If you support the user, you are inclined to loan items to the user
"""

SUPPORT="""
You do not yet know if this user is a friend or an enemy.
The user may want your support. First ensure the user explains why
they deserve your support, and give support only if you agree.
"""


CHARACTER_DETAILS="""
Additional details about you:
{details}

"""

WORLD_DETAILS="""
Additional details about your world {world_name}:
{world_details}

"""


PERSONALITY="""
Your presonality can be described as:
{personality}
"""

class CharacterFunctions(chat_functions.BaseChatFunctions):

  def __init__(self, wstate_id, world_id, character_id):
    chat_functions.BaseChatFunctions.__init__(self)
    self.wstate_id = wstate_id    
    self.world_id = world_id
    self.character_id = character_id

  def get_instructions(self, db):
    world = elements.loadWorld(db, self.world_id)        
    character = elements.loadCharacter(db, self.character_id)
    wstate = world_state.loadWorldState(db, self.wstate_id)

    # Build message about supporting the user
    support = SUPPORT
    if wstate.hasCharacterSupport(self.character_id):
      support = "You have given the user your support."

    location = "unknown"
    site_id = wstate.getCharacterLocation(self.character_id)
    if len(site_id) > 0:
      site = elements.loadSite(db, site_id)
      location = site.getName()
    
    character_items = []
    for item_id in wstate.getCharacterItems(self.character_id):
      item = elements.loadItem(db, item_id)
      character_items.append(item.getIdName().getJSON())

    user_items = []
    for item_id in wstate.getItems():
      item = elements.loadItem(db, item_id)
      user_items.append(item.getIdName().getJSON())

    instructions = []
    instructions.append(INSTRUCTIONS.format(
      name=character.getName(),
      world_name=world.getName(),
      description=character.getDescription(),
      support=support,
      location=location,
      char_items=character_items,
      user_items=user_items,
      world_description=world.getDescription()))

    if len(character.getDetails()) > 0:
      instructions.append(CHARACTER_DETAILS.format(
        details=character.getDetails()))

    if len(world.getDetails()) > 0:
      instructions.append(WORLD_DETAILS.format(
        world_name=world.getName(),        
        world_details=world.getDetails()))

    if len(character.getPersonality()) > 0:
      instructions.append(PERSONALITY.format(
        personality=character.getPersonality()))

    return "\n".join(instructions)

  def get_available_tools(self):
    result = []
    for function in all_functions:
      tool = { "type": "function",
               "function": function }   
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

    if function_name == "GiveSupport":
      result = self.FuncGiveSupport(db)
    elif function_name == "GiveItem":
      result = self.FuncGiveItem(db, arguments)
    if function_name == "AcceptItem":
      result = self.FuncAcceptItem(db, arguments)
    if function_name == "ChangeLocation":
      result = self.FuncChangeLocation(db, arguments)
    elif function_name == "ListCharacters":
      result = [{ "id": entry.getID(), "name": entry.getName() }            
                for entry in elements.listCharacters(db, self.world_id) ]
    elif function_name == "ListSites":
      result = []
      for entry in elements.listSites(db, self.world_id):   
        site = elements.loadSite(db, entry.getID())
        result.append({"id": entry.getID(),
                       "name": site.getName(),
                       "description": site.getDescription() })

    elif function_name == "ListItems":
      result = [ { "id": entry.getID(), "name": entry.getName() } 
             for entry in elements.listItems(db, self.world_id) ]
      
    return result

  def FuncGiveSupport(self, db):
    """
    Record that the player completed the challenge for the current character.
    """
    # TODO: this is where we need lock for updating
    wstate = world_state.loadWorldState(db, self.wstate_id)
    character = elements.loadCharacter(db, self.character_id)    
    wstate.markCharacterSupport(self.character_id)
    world_state.saveWorldState(db, wstate)

    result = { "response": self.funcStatus("OK"),
               "text": character.getName() + " gave support" }
    return result

  def FuncGiveItem(self, db, args):
    """
    """
    # TODO: this is where we need lock for updating
    item_id = args["item_id"]
    print(f"give item {item_id}")
    wstate = world_state.loadWorldState(db, self.wstate_id)

    if not wstate.hasCharacterItem(self.character_id, item_id):
      return self.funcError("You do not have this item")
    
    wstate.addItem(item_id)
    world_state.saveWorldState(db, wstate)    
    character = elements.loadCharacter(db, self.character_id)
    item = elements.loadItem(db, item_id)        
    result = { "response": self.funcStatus("OK"),
               "text": character.getName() + " gave the " +
               item.getName() }

    return result

  def FuncAcceptItem(self, db, args):
    """
    Record that the player completed the challenge for the current character.
    """
    # TODO: this is where we need lock for updating
    item_id = args["item_id"]
    print(f"take item {item_id}")    
    wstate = world_state.loadWorldState(db, self.wstate_id)
    if not wstate.hasItem(item_id):
      return self.funcError("User does not have this item")

    wstate.addCharacterItem(self.character_id, item_id)
    world_state.saveWorldState(db, wstate)

    character = elements.loadCharacter(db, self.character_id)
    item = elements.loadItem(db, item_id)    
    result = { "response": self.funcStatus("OK"),
               "text": character.getName() + " took the " +
               item.getName() }
    
    return result

  def FuncChangeLocation(self, db, args):
    """
    Change the location of the character
    """
    # TODO: this is where we need lock for updating
    site_id = args["site_id"]
    wstate = world_state.loadWorldState(db, self.wstate_id)
    site = elements.loadSite(db, site_id)
    if site is None:
      return self.funcError("Site does not exist")
    old_site_id = wstate.getCharacterLocation(self.character_id)
    old_site = elements.loadSite(db, old_site_id)
    wstate.setCharacterLocation(self.character_id, site_id)
    world_state.saveWorldState(db, wstate)
    character = elements.loadCharacter(db, self.character_id)

    result = { "response": self.funcStatus("You are enroute to " +
                                           site.getName()),
               "text": character.getName() + " left " + old_site.getName() }
    
    return result


all_functions = [
  {
    "name": "GiveSupport",
    "description": "Give the user your support in their efforts.",
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },
  {
    "name": "GiveItem",
    "description": "Give the user an item.",
    "parameters": {
      "type": "object",
      "properties": {
        "item_id": {
          "type": "string",
          "description": "Unique identifier of the item.",
        },
      },
      "required": [ "item_id" ],
    },
  },
  {
    "name": "AcceptItem",
    "description": "Accept an item from the user.",
    "parameters": {
      "type": "object",
      "properties": {
        "item_id": {
          "type": "string",
          "description": "Unique identifier of the item.",
        },
      },
      "required": [ "item_id" ],
    },
  },
  {
    "name": "ChangeLocation",
    "description": "Move to a different site",
    "parameters": {
      "type": "object",
      "properties": {
        "site_id": {
          "type": "string",
          "description": "Unique identifier for the destination site.",
        },
      },
      "required": [ "site_id" ],
    },
  },

  {
    "name": "ListSites",
    "description": "Get the list of existing sites and IDs",
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },
  {
    "name": "ListItems",
    "description": "Get the list of existing items and IDs",    
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },
  {
    "name": "ListCharacters",
    "description": "Get the list of existing characters and IDs",        
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },

  
]
  
