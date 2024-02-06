import json
import os
import logging


from . import elements
from . import chat_functions
from . import world_state

INSTRUCTIONS="""

You are an actor playing '{name}', a fictional character our story. Given the following character description, personality, goals, emotional state, adopt the personality described and respond as the character in a physical world.

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

{char_state}
{user_state}

If you favor Travler, call IncreaseFriendship, otherwise call DecreaseFriendship.
"""

CHAR_ITEMS="""
{name} possesses interesting items.
"""

NO_CHAR_ITEMS="""
{name} does not currently possess any items.
"""

USER_ITEMS="""
Travler is holding an interesting item: '{selected_item}'
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

  def getProperties(self):
    properties = super().getProperties()
    properties["wstate_id"] = self.wstate_id
    properties["world_id"] = self.world_id
    properties["character_id"] = self.character_id
    return properties

  def setProperties(self, properties):
    super().setProperties(properties)
    self.wstate_id = properties["wstate_id"]
    self.world_id = properties["world_id"]
    self.character_id = properties["character_id"]

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
    
    if len(wstate.getCharacterItems(self.character_id)) > 0:
      character_state=CHAR_ITEMS.format(
        name=character.getName())
    else:
      character_state=NO_CHAR_ITEMS.format(
        name=character.getName())

    user_state = []
        
    # Invisibility
    invisible = world_state.CharStatus.INVISIBLE    
    if wstate.hasPlayerStatus(invisible):
      user_state.append("Traveler is here, but invisible. You can not see them")
    else:
      user_state.append("You can see that Traveler is here with you at %s" %
                        location)
      # Selected item
      if wstate.getSelectedItem() != None:
        item = elements.loadItem(db, wstate.getSelectedItem())
        user_state.append(USER_ITEMS.format(
          selected_item=item.getName()))
      # Injured -  TODO

    # Convert into a string.
    user_state = '\n'.join(user_state)
    
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
      char_state=character_state,
      user_state=user_state,
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
    if function_name == "ChangeLocation":
      result = self.FuncChangeLocation(db, arguments)
    elif function_name == "ListCharacters":
      result = [{ "name": entry.getName() }            
                for entry in elements.listCharacters(db, self.world_id) ]
    elif function_name == "ListSites":
      result = []
      for entry in elements.listSites(db, self.world_id):   
        site = elements.loadSite(db, entry.getID())
        result.append({ "name": site.getName(),
                        "description": site.getDescription() })

    elif function_name == "ListItems":
      result = []
      for entry in elements.listItems(db, self.world_id):
        item = elements.loadItem(db, entry.getID())
        result.append({ "name": item.getName(),
                        "description": item.getDescription() })
    elif function_name == "ListMyItems":
      wstate = world_state.loadWorldState(db, self.wstate_id)      
      result = []
      char_items = wstate.getCharacterItems(self.character_id)
      for entry in elements.listItems(db, self.world_id):
        if entry.getID() in char_items:
          item = elements.loadItem(db, entry.getID())
          result.append({ "name": item.getName(),
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
    Give or receive an item
    """
    # TODO: this is where we need lock for updating
    item_name = args["name"]
    print(f"give item {name}")
    wstate = world_state.loadWorldState(db, self.wstate_id)
    item = elements.findFind(db, self.world_id, item_name)
    if item is None:
      return self.funcError(f"Not a valid item id. Perhaps call ListItems")

    character = elements.loadCharacter(db, self.character_id)
    text = ""
    if wstate.hasCharacterItem(self.character_id, item_id):
      # Charracter has item to give to the user
      wstate.addItem(item_id)
      text = character.getName() + " gave the " + item.getName()       
    elif wstate.hasItem(item_id):
      # User has item to give to the character
      wstate.addCharacterItem(self.character_id, item_id)
      text = character.getName() + " accepted the " + item.getName()
      if wstate.getSelectedItem() == item_id:
        wstate.selectItem(None)
    else:
      return self.funcError("Niether you or the user have this item")

    world_state.saveWorldState(db, wstate)    
    result = { "response": self.funcStatus("OK"),
               "text": text }

    return result


  def FuncChangeLocation(self, db, args):
    """
    Change the location of the character
    """
    # TODO: this is where we need lock for updating
    site_name = args["name"]
    wstate = world_state.loadWorldState(db, self.wstate_id)
    site = elements.findSite(db, self.world_id, site_name)
    if site is None:
      return self.funcError("Site does not exist Perhaps call ListSites?")
    old_site_id = wstate.getCharacterLocation(self.character_id)
    if old_site_id == site.id:
      return self.funcError("You are already at %s." % site.getName())
    old_site = elements.loadSite(db, old_site_id)
    wstate.setCharacterLocation(self.character_id, site.id)
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
    "description": "Give or recieve an item.",
    "parameters": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "Name of the item.",
        },
      },
      "required": [ "name" ],
    },
  },
  {
    "name": "ChangeLocation",
    "description": "Move to a different site",
    "parameters": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "Name of the destination site.",
        },
      },
      "required": [ "name" ],
    },
  },

  {
    "name": "ListSites",
    "description": "Get the list of existing sites",
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },
  {
    "name": "ListItems",
    "description": "Get the list of all existing items",    
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },
  {
    "name": "ListMyItems",
    "description": "Get the list of items the character possesses",
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },
  {
    "name": "ListCharacters",
    "description": "Get the list of all existing characters",        
    "parameters": {
      "type": "object",
      "properties": {
      },
    },
  },

  
]
  
