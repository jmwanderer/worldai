import json
import os
import logging


from . import elements
from . import chat_functions
from . import world_state
from . import info_set

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

Note the state of friendship with IncreaseFriendship and DecreaseFriendship.
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
You are not friendly with the user. You do not trust them.
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
    poisoned = world_state.CharStatus.POISONED
    paralized = world_state.CharStatus.PARALIZED
    
    if wstate.hasPlayerStatus(invisible):
      user_state.append("Traveler is here, but invisible. You can not see them")
    else:
      user_state.append("You can see that Traveler is here with you at %s" %
                        location)
      if wstate.hasPlayerStatus(poisoned):
        user_state.append("Traveler appears to be poisoned")
      if wstate.hasPlayerStatus(paralized):
        user_state.append("Traveler appears to be paralized")
      if wstate.getPlayerHealthPercent() < 25:
        user_state.append("Traveler is gravely injured")
      elif wstate.getPlayerHealthPercent() < 100:
        user_state.append("Traveler is injured")
        
      # Selected item
      if wstate.getSelectedItem() != None:
        item = elements.loadItem(db, wstate.getSelectedItem())
        user_state.append(USER_ITEMS.format(
          selected_item=item.getName()))

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
    elif function_name == "DecreaseFriendship":
      result = self.FuncDecreaseFriendship(db)
    elif  function_name == "LookupInformation":
      result = self.FuncLookupInformation(db, arguments)
    elif function_name == "GiveItem":
      result = self.FuncGiveItem(db, arguments)
    elif function_name == "UseItem":
      result = self.FuncUseItem(db, arguments)
    if function_name == "ChangeLocation":
      result = self.FuncChangeLocation(db, arguments)
    elif function_name == "ListCharacters":
      result = [{ "name": entry.getName() }            
                for entry in elements.listCharacters(db, self.world_id) ]
    elif function_name == "ListSites":
      result = []
      wstate = world_state.loadWorldState(db, self.wstate_id)
      for entry in elements.listSites(db, self.world_id):   
        site = elements.loadSite(db, entry.getID())
        result.append({ "name": site.getName(),
                        "description": site.getDescription(),
                        "locked": wstate.isSiteLocked(id) })
    elif function_name == "ListItems":
      result = []
      for entry in elements.listItems(db, self.world_id):
        item = elements.loadItem(db, entry.getID())
        result.append({ "name": item.getName(),
                        "description": item.getDescription(),
                        "mobile": item.getIsMobile(),
                        "function": item.getAbility().effect })
    elif function_name == "ListMyItems":
      wstate = world_state.loadWorldState(db, self.wstate_id)      
      result = []
      char_items = wstate.getCharacterItems(self.character_id)
      for entry in elements.listItems(db, self.world_id):
        if entry.getID() in char_items:
          item = elements.loadItem(db, entry.getID())
          result.append({ "name": item.getName(),
                          "description": item.getDescription(),
                          "mobile": item.getIsMobile(),
                          "function": item.getAbility().effect })
    return result

  def FuncIncreaseFriendship(self, db):
    """
    Record that the player completed the challenge for the current character.
    """
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
    # TODO: this is where we need lock for updating
    wstate = world_state.loadWorldState(db, self.wstate_id)
    character = elements.loadCharacter(db, self.character_id)    
    wstate.decreaseFriendship(self.character_id)
    world_state.saveWorldState(db, wstate)

    result = { "response": self.funcStatus("OK"),
               "text": character.getName() + " increases enimity" }
    return result

  def FuncLookupInformation(self, db, args):
    """
    Consult knowledge base for information.
    """
    context = args["context"]
    logging.info("Lookup info: %s" % context)
    embed = info_set.generateEmbedding(context)
    content = info_set.getInformation(db, self.world_id, embed, 2)
    return { "context": context,
            "information": content }
  
  def FuncGiveItem(self, db, args):
    """
    Give or receive an item
    """
    # TODO: this is where we need lock for updating
    item_name = args["name"]
    print(f"give item {item_name}")
    wstate = world_state.loadWorldState(db, self.wstate_id)
    item = elements.findItem(db, self.world_id, item_name)
    if item is None:
      return self.funcError(f"Not an existing item. Perhaps call ListMyItems?")

    character = elements.loadCharacter(db, self.character_id)
    text = ""
    if wstate.hasCharacterItem(self.character_id, item.id):
      # Charracter has item to give to the user
      wstate.addItem(item.id)
      text = character.getName() + " gave the " + item.getName()       
    elif wstate.hasItem(item.id):
      # User has item to give to the character
      wstate.addCharacterItem(self.character_id, item.id)
      text = character.getName() + " accepted the " + item.getName()
      if wstate.getSelectedItem() == item.id:
        wstate.selectItem(None)
    else:
      return self.funcError("Niether you or the user have this item")

    world_state.saveWorldState(db, wstate)    
    result = { "response": self.funcStatus("OK"),
               "text": text }

    return result

  def FuncUseItem(self, db, args):
    """
    Character invoking the function of an item
    """
    item_name = args["name"]
    wstate = world_state.loadWorldState(db, self.wstate_id)
    item = elements.findItem(db, self.world_id, item_name)
    if item is None:
      return self.funcError(f"Not a valid item. Perhaps call ListMyItems")

    character = elements.loadCharacter(db, self.character_id)
    text = ""

    # Check if character has the item
    if item.getIsMobile():
      if not wstate.hasCharacterItem(self.character_id, item.id):
        return self.funcError(f"You do not have this item. " +
                              "Perhaps call ListMyItems")
    else:
      if (wstate.getItemLocation(item.id) !=
          wstate.getCharacterLocation(self.character_id)):
        return self.funcError(f"This item is not here")

    # Character can use the item
    # Apply an effect
    impact = None
    
    match item.getAbility().effect:
      case elements.ItemEffect.HEAL:
        impact = self.healPlayer(wstate)
      case elements.ItemEffect.HURT:
        impact = self.hurtPlayer(wstate)
      case elements.ItemEffect.PARALIZE:
        impact = self.paralizePlayer(wstate)
        pass                
      case elements.ItemEffect.POISON:
        impact = self.poisonPlayer(wstate)
        pass                
      case elements.ItemEffect.SLEEP:
        pass                
      case elements.ItemEffect.BRAINWASH:
        pass                
      case elements.ItemEffect.CAPTURE:
        pass
      case elements.ItemEffect.INVISIBILITY:
        pass
      case elements.ItemEffect.UNLOCK:
        impact = self.unlockSite(db, wstate, item)
        pass
        
    
    text = character.getName() + " used " + item.getName() + "."
    if impact is not None:
      fulltext = text + impact
    else:
      impact = "None"
      fulltext = text
    world_state.saveWorldState(db, wstate)    
    result = { "action": text,
               "result": impact,
               "text": fulltext }

    return result

  

  def healPlayer(self, wstate):
    if not wstate.isPlayerHealthy():
      message = " Travler is healed"
      wstate.healPlayer()
    else:
      message = "Travler is already healthy"
    return message

  def hurtPlayer(self, wstate):
    health = wstate.getPlayerHealth() - 4
    if health < 0:
      health = 0
    wstate.setPlayerHealth(health)
    if wstate.isPlayerDead():
      message = "Travler is killed"
    else:
      message = "Travler is harmed"
    return message

  def poisonPlayer(self, wstate):
    wstate.addPlayerStatus(world_state.CharStatus.POISONED)
    message = "Travler is poisoned"
    return message

  def paralizePlayer(self, wstate):
    wstate.addPlayerStatus(world_state.CharStatus.PARALIZED)
    message = "Travler is paralized"
    return message

  def unlockSite(self, db, wstate, item):
    site_id = item.getAbility().site_id
    site = elements.loadSite(db, site_id)
    message = ""
    if site is not None:
      if wstate.isSiteLocked(site_id):
        wstate.setSiteLocked(site_id, False)
        message = f"Site {site.getName()} is now unlocked."
      else:
        message = f"Site {site.getName()} is already unlocked."
    return message
  

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
    if wstate.isSiteLocked(site.id):
      return self.funcError("The site is locked and can not be accessed")
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
    "name": "UseItem",
    "description": "Invoke the function of an item.",
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
  {
    "name": "LookupInformation",
    "description": "Check knowledge base for information",
    "parameters": {
      "type": "object",
      "properties": {
        "context": {
          "type": "string",
          "descripton": "Context of the information query"
        }
      }
    }
  }
  
]
  
