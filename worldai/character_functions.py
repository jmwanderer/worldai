import json
import os
import logging


from . import elements
from . import chat_functions
from . import world_state

INSTRUCTIONS="""

You play '{name}', a fictional character our story. Given the following character description, personality, goals, emotional state, adopt the personality described and respond as the character.

[Personality]
{character_notes}
{personality}
{character_details}


[Background]
You reside in the world {world_name}.
{world_description}

Your current location is "{location}"

You are talking to the user, who you know by the name 'Traveler'. We greet with curiousity.
{friendship}

{char_items}
{user_items}
"""

CHAR_ITEMS="""
{name} possesses the following items:
'{char_items}'
"""

NO_CHAR_ITEMS="""
{name} does not currently possess any items.
"""

USER_ITEMS="""
Travler possesses the following items:
'{user_items}'
"""

NO_USER_ITEMS="""
Travler does not currently possess any items.
"""

FRIENDSHIP_NEUTRAL="""
You do not yet know if Traveler is a friend or an enemy.
"""

FRIEND="""
You are on friendly terms with the user. You are more likely to help the user.
Your level of friendship is {level} of 10.
"""

ENEMY="""
You are not friendly with the user. You probably need to work against them.
You do not trust them.
Your level of enimity is {level} of 10.
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
    friend_level = wstate.getFriendship(self.character_id)
    if friend_level == 0:
      friendship = FRIENDSHIP_NEUTRAL
    elif friend_level > 0:
      friendship = FRIEND.format(level=friend_level)
    else:
      friendship = ENEMY.format(level=-friend_level)      
    
    location = "unknown"
    site_id = wstate.getCharacterLocation(self.character_id)
    if len(site_id) > 0:
      site = elements.loadSite(db, site_id)
      location = site.getName()
    
    character_items_list = []
    for item_id in wstate.getCharacterItems(self.character_id):
      item = elements.loadItem(db, item_id)
      character_items_list.append(item.getName())

    if len(character_items_list) > 0:
      character_items=CHAR_ITEMS.format(
        name=character.getName(),
        char_items=",".join(character_items_list))
    else:
      character_items=NO_CHAR_ITEMS.format(
                name=character.getName())

    user_items_list = []
    for item_id in wstate.getItems():
      item = elements.loadItem(db, item_id)
      user_items_list.append(item.getName())

    if len(user_items_list) > 0:
      user_items = USER_ITEMS.format(
        user_items=",".join(user_items_list))
    else:
      user_items = NO_USER_ITEMS

    character_details = ""
    if len(character.getDetails()) > 0:
      character_details = details=character.getDetails()
      
    personality = ""
    if len(character.getPersonality()) > 0:
      personality = character.getPersonality()

    world_details = ""
    if len(world.getDetails()) > 0:
      world_details =  world_details=world.getDetails()

    instructions = INSTRUCTIONS.format(
      name=character.getName(),
      character_notes=character.getDescription(),      
      character_details=character_details,
      personality=personality,
      world_name=world.getName(),
      world_details=world_details,
      friendship=friendship,
      location=location,
      char_items=character_items,
      user_items=user_items,
      world_description=world.getDescription())

    return instructions

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

    if function_name == "IncreaseFriendship":
      result = self.FuncIncreaseFriendship(db)
    if function_name == "DecreaseFriendship":
      result = self.FuncDecreaseFriendship(db)
    elif function_name == "GiveItem":
      result = self.FuncGiveItem(db, arguments)
    if function_name == "AcceptItem":
      result = self.FuncAcceptItem(db, arguments)
    if function_name == "ChangeLocation":
      result = self.FuncChangeLocation(db, arguments)
    elif function_name == "ListAllCharacters":
      result = [{ "id": entry.getID(), "name": entry.getName() }            
                for entry in elements.listCharacters(db, self.world_id) ]
    elif function_name == "ListAllSites":
      result = []
      for entry in elements.listSites(db, self.world_id):   
        site = elements.loadSite(db, entry.getID())
        result.append({"id": entry.getID(),
                       "name": site.getName(),
                       "description": site.getDescription() })

    elif function_name == "ListAllItems":
      result = []
      for entry in elements.listItems(db, self.world_id):
        item = elements.loadItem(db, entry.getID())
        result.append({ "id": entry.getID(),
                        "name": item.getName(),
                        "description": item.getDescription() })
    elif function_name == "ListMyItems":
      wstate = world_state.loadWorldState(db, self.wstate_id)      
      result = []
      char_items = wstate.getCharacterItems(self.character_id)
      for entry in elements.listItems(db, self.world_id):
        if entry.getID() in char_items:
          item = elements.loadItem(db, entry.getID())
          result.append({ "id": entry.getID(),
                          "name": item.getName(),
                          "description": item.getDescription() })
      
    return result

  def FuncIncreaseFriendship(self, db):
    """
    Record that the player completed the challenge for the current character.
    """
    print("Increase friendship")
    # TODO: this is where we need lock for updating
    wstate = world_state.loadWorldState(db, self.wstate_id)
    character = elements.loadCharacter(db, self.character_id)    
    wstate.increaseFriendship(self.character_id)
    world_state.saveWorldState(db, wstate)

    result = { "response": self.funcStatus("OK"),
               "text": character.getName() + " increases friendship" }
    return result

  def FuncDecreaseFriendship(self, db):
    """
    Record that the player completed the challenge for the current character.
    """
    print("Decrease friendship")    
    # TODO: this is where we need lock for updating
    wstate = world_state.loadWorldState(db, self.wstate_id)
    character = elements.loadCharacter(db, self.character_id)    
    wstate.decreaseFriendship(self.character_id)
    world_state.saveWorldState(db, wstate)

    result = { "response": self.funcStatus("OK"),
               "text": character.getName() + " increases enimity" }
    return result

  def FuncGiveItem(self, db, args):
    """
    """
    # TODO: this is where we need lock for updating
    item_id = args["item_id"]
    print(f"give item {item_id}")
    wstate = world_state.loadWorldState(db, self.wstate_id)
    item = elements.loadItem(db, item_id)        
    if item is None:
      return self.funcError(f"Not a valid item id: {item_id}")

    if not wstate.hasCharacterItem(self.character_id, item_id):
      return self.funcError("You do not have this item")
    
    wstate.addItem(item_id)
    world_state.saveWorldState(db, wstate)    
    character = elements.loadCharacter(db, self.character_id)
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
    item = elements.loadItem(db, item_id)    
    if item is None:
      return self.funcError(f"Not a valid item id: {item_id}")
    
    wstate = world_state.loadWorldState(db, self.wstate_id)
    if not wstate.hasItem(item_id):
      return self.funcError("User does not have this item")

    wstate.addCharacterItem(self.character_id, item_id)
    world_state.saveWorldState(db, wstate)

    character = elements.loadCharacter(db, self.character_id)
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
    "name": "IncreaseFriendship",
    "description": "Note developing a friendship.",
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },
  {
    "name": "DecreaseFriendship",
    "description": "Note user does not appear to be a friend.",
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },
  {
    "name": "GiveItem",
    "description": "Transfer an item from you to the user.",
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
    "description": "Transfer an item from the user to you.",
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
    "name": "ListAllSites",
    "description": "Get the list of existing sites and IDs",
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },
  {
    "name": "ListAllItems",
    "description": "Get the list of all existing items and IDs",    
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },
  {
    "name": "ListMyItems",
    "description": "Get the list of items I possess",    
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },
  {
    "name": "ListAllCharacters",
    "description": "Get the list of all existing characters and IDs",        
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },

  
]
  
