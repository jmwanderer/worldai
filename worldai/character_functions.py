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
You do not yet know if this user is a friend or an enemy.

{support}

You are currently located in {location}

You have the following items:
{char_items}

The user has the following items:
{user_items}

Your world is described as follows:
{world_description}

When taking an item from the user, call TakeItem
When giving an item to the user, call GiveItem
To offer your support to the user, call GiveSupport

"""

SUPPORT="""
The user may want your support. First ensure the user explains why
they deserve your support, and give spport only if you agree.
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
    if function_name == "TakeItem":
      result = self.FuncTakeItem(db, arguments)

    return result

  def FuncGiveSupport(self, db):
    """
    Record that the player completed the challenge for the current character.
    """
    # TODO: this is where we need lock for updating
    wstate = world_state.loadWorldState(db, self.wstate_id)
    wstate.markCharacterSupport(self.character_id)
    world_state.saveWorldState(db, wstate)
    return self.funcStatus("OK")

  def FuncGiveItem(self, db, args):
    """
    """
    # TODO: this is where we need lock for updating
    item_id = args["item_id"]
    print(f"give item {item_id}")
    wstate = world_state.loadWorldState(db, self.wstate_id)

    if not wstate.removeCharacterItem(self.character_id, item_id):
      return self.funcError("You do not have this item")
    
    if not wstate.addItem(item_id):
      return self.funcError("Already has the item")
    
    world_state.saveWorldState(db, wstate)
    return self.funcStatus("OK")

  def FuncTakeItem(self, db, args):
    """
    Record that the player completed the challenge for the current character.
    """
    # TODO: this is where we need lock for updating
    item_id = args["item_id"]
    print(f"take item {item_id}")    
    wstate = world_state.loadWorldState(db, self.wstate_id)
    if not wstate.removeItem(item_id):
      return self.funcError("User does not have this item")

    wstate.addCharacterItem(self.character_id, item_id)
    world_state.saveWorldState(db, wstate)
    return self.funcStatus("OK")


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
    "name": "TakeItem",
    "description": "Take an item from the user.",
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
]
  
