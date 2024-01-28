"""
Implements the game play commands.
"""
import logging
import pydantic
import typing
import enum


from . import elements
from . import world_state

class StatusCode(str, enum.Enum):
  ok = 'ok'
  error = 'error'

class CallStatus(pydantic.BaseModel):
  result: StatusCode = StatusCode.ok
  message: typing.Optional[str] = ""

class CommandName(str, enum.Enum):
  go = 'go'
  take = 'take'
  select = 'select'  
  use = 'use'  
  engage = 'engage'
  disengage = 'disengage'

class Command(pydantic.BaseModel):
  """
  Represents state for a instance of a character
  Either a player or an NPC
  """
  name: CommandName
  to: typing.Optional[str] = None
  item: typing.Optional[str] = None
  character: typing.Optional[str] = None

class CommandResponse(pydantic.BaseModel):
  """
  Response to a client command
  """
  message: str = ""
  status: CallStatus = CallStatus()
  changed: bool = False


class ClientActions:
  def __init__(self, db, world, wstate):
    self.db = db
    self.world = world
    self.wstate = wstate

  def ExecCommand(self, command):
    """
    Implement a command from the client.
    Return a json result for the client
    """
    response = CommandResponse()

    if command.name == CommandName.go:
      site_id = command.to
      # Verify location
      site = elements.loadSite(self.db, site_id)
      if site is not None:
        self.wstate.setLocation(site_id)
        logging.info("GO: set location %s",  site_id)
        response.message = f"Go {site.getName()}"
        self.wstate.advanceTime(30)
      else:
        self.wstate.setLocation("")
        logging.info("GO: clear location")        
      response.changed = True
      
    elif command.name == CommandName.take:
      item_id = command.item
      logging.info("take item %s", item_id)
      
      # Verify 
      if self.wstate.getItemLocation(item_id) == self.wstate.getLocation():
        item = elements.loadItem(self.db, item_id)
        if item.getIsMobile():
          self.wstate.addItem(item_id)
          response.changed = True
          response.message = f"You picked up {item.getName()}"

    elif command.name == CommandName.select:
      item_id = command.item
      if item_id is None or len(item_id) == 0:
        self.wstate.selectItem("")
        response.changed = True
      else:
        logging.info("select item %s", item_id)
        if self.wstate.hasItem(item_id):
          item = elements.loadItem(self.db, item_id)
          self.wstate.selectItem(item_id)
          response.changed = True
          response.message = f"You are holding {item.getName()}"

    elif command.name == CommandName.use:
      item = elements.loadItem(self.db, command.item)
      if item is None:
        response.status.result = StatusCode.error
      elif self.UseItem(item, command.character, response):
        logging.info("use item %s", command.item)
        # TODO: change to result of use
        response.changed = True
        self.wstate.advanceTime(5)        
      else:
        response.message = f"Unable to use {item.getName()}"

    elif command.name == CommandName.engage:
      character_id = command.character
      character = elements.loadCharacter(self.db, character_id)
      self.wstate.setChatCharacter(character_id)
      logging.info("engage character %s", character_id)
      logging.info("ENGAGE: location: %s", self.wstate.getLocation())   
      response.changed = True
      if not self.wstate.isCharacterDead(character_id):
        response.message = f"Talking to {character.getName()}"
      else:
        response.message = f"{character.getName()} is dead"
      self.wstate.advanceTime(5)

    elif command.name == CommandName.disengage:
      self.wstate.setChatCharacter(None)
      logging.info("disengage character")
      response.changed = True
      response.message = f"Talking to nobody"

    logging.info("Client command response: %s", response.model_dump())
    return response
  

  def UseItem(self, item, cid, response):
    """
    cid is optional
    """
    logging.info("Use item %s character id %s" % (item.getName(), cid));
    # May be None
    character = elements.loadCharacter(self.db, cid)
    # Guard against unexpected inputs
    if character is None:
      cid = None

    if item.getIsMobile():
      # Verify user has the item
      if not self.wstate.hasItem(item.id):
        logging.info("item %s is mobile, but user does not possess",
                     item.getName())
        return False
    else:
      # Verify same location
      if self.wstate.getItemLocation(item.id) != self.wstate.getLocation():
        logging.info("item %s is not mobile and not in same location",
                     item.getName())
        return False

    sleeping = world_state.CharStatus.SLEEPING
    poisoned = world_state.CharStatus.POISONED
    paralized = world_state.CharStatus.PARALIZED
    brainwashed = world_state.CharStatus.BRAINWASHED
    captured = world_state.CharStatus.CAPTURED
    invisible = world_state.CharStatus.INVISIBLE
    logging.info("use item - %s", item.getAbility().effect)    

    # Apply an effect
    response.message = f"Nothing happened"    
    match item.getAbility().effect:
      case elements.ItemEffect.HEAL:
        # Self or other
        if cid is None:
          if not self.wstate.isPlayerHealthy():
            response.message = "You are healed"
            self.wstate.healPlayer()
          else:
            response.message = "You are already heathly"
        else:
          if not self.wstate.isCharacterDead(cid):
            if not self.wstate.isCharacterHealthy(cid):
              self.wstate.healCharacter(cid)
              response.message = f"{character.getName()} is healed"
            else:
              response.message = f"{character.getName()} is already healthy"
            
      case elements.ItemEffect.HURT:
        # Only other TODO: extend so characters can use
        if cid is not None:
          health = self.wstate.getCharacterHealth(cid) - 4
          if health < 0:
            health = 0
          self.wstate.setCharacterHealth(cid, health)
          if self.wstate.isCharacterDead(cid):          
            response.message = f"{character.getName()} is dead"
          else:
            response.message = f"{character.getName()} took damage"
            

      case elements.ItemEffect.PARALIZE:
        # Only other TODO: extend so characters can use
        if cid is not None:
          self.wstate.addCharacterStatus(cid, paralized)
          response.message = f"{character.getName()} is paralized"    
            
      case elements.ItemEffect.POISON:
        # Other
        if cid is not None:
          self.wstate.addCharacterStatus(cid, poisoned)
          response.message = f"{character.getName()} is poisoned"

      case elements.ItemEffect.SLEEP:
        # Other character
        if cid is not None:
          self.wstate.addCharacterStatus(cid, sleeping)
          response.message = f"{character.getName()} is sleeping"
              
      case elements.ItemEffect.BRAINWASH:
        # Other character
        if cid is not None:
          self.wstate.addCharacterStatus(cid, brainwashed)
          response.message = f"{character.getName()} is brainwashed"          
            
      case elements.ItemEffect.CAPTURE:
        # Other character - toggle
        if cid is not None:
          if self.wstate.hasCharacterStatus(cid, captured):
            self.wstate.removeCharacterStatus(cid, captured)
            response.message = f"{character.getName()} is released"
          else:
            self.wstate.addCharacterStatus(cid, captured)
            response.message = f"{character.getName()} is captured"
            
      case elements.ItemEffect.INVISIBILITY:
        # Self only - toggle
        if self.wstate.hasPlayerStatus(invisible):
          self.wstate.removePlayerStatus(invisible)
          response.message = "You are now visible"          
        else:
          self.wstate.addPlayerStatus(invisible)
          response.message = "You are invisible"

      case elements.ItemEffect.UNLOCK:
        site_id = item.getAbility().side_id
        site = elements.loadSite(site_id)
        if site is not None:
          self.wstate.setSiteLocked(side_id, False)
          response.message = f"Site {site.getName()} is now unlocked."
        
    return True

class ElemInfo(pydantic.BaseModel):
  id: str = ""
  name: str = ""
  description: str = ""

class CharacterData(pydantic.BaseModel):
  id: str = ""
  name: str = ""
  description: str = ""
  sleeping: bool = False
  paralized: bool = False
  poisoned: bool = False
  brainwashed: bool = False
  captured: bool = False
  invisible: bool = False
  location: str = ""
  credits: int = 0
  health: int = 0
  strength: int = 0
  friendship: int = 0
  can_chat: bool = True
  inventory: typing.List[ ElemInfo ] = []


def LoadCharacterData(db, world, wstate, cid):
  data = CharacterData()
  character = elements.loadCharacter(db, cid)
  if character is None:
    return { "error": f"character {cid} does not exist"}
  
  data.name = character.getName()
  data.description = character.getDescription()
  sleeping = world_state.CharStatus.SLEEPING
  data.sleeping = wstate.hasCharacterStatus(cid, sleeping)
  paralized = world_state.CharStatus.PARALIZED
  data.paralized = wstate.hasCharacterStatus(cid, paralized)
  poisoned = world_state.CharStatus.POISONED
  data.poisoned = wstate.hasCharacterStatus(cid, poisoned)
  brainwashed = world_state.CharStatus.BRAINWASHED
  data.brainwashed = wstate.hasCharacterStatus(cid, brainwashed)
  captured = world_state.CharStatus.CAPTURED
  data.captured= wstate.hasCharacterStatus(cid, captured)  
  invisible = world_state.CharStatus.INVISIBLE
  data.invisible = wstate.hasCharacterStatus(cid, invisible)
  data.location = wstate.getCharacterLocation(cid)
  data.credits = wstate.getCharacterCredits(cid)
  data.health = wstate.getCharacterHealthPercent(cid)
  data.strength = wstate.getCharacterStrengthPercent(cid)
  data.friendship = wstate.getFriendship(cid)

  for item_id in wstate.getCharacterItems(cid):
    item = elements.loadItem(db, item_id)
    if item is None:
      logging.error("unknown item in inventory: %s", item_id)
    else:
      item_info = ElemInfo()
      item_info.id = item_id
      item_info.name = item.getName()
      item_info.description = item.getDescription()
      data.inventory.append(item_info)

  # Check if character can chat with player
  if (data.sleeping or wstate.isCharacterDead(cid) or
      data.location != wstate.getLocation()):
    data.can_chat = False
  
  return data
  

class PlayerData(pydantic.BaseModel):
  """
  Vital stats for the player character
  """
  status: CharacterData = CharacterData()
  selected_item: typing.Optional[str] = None
  chat_who: str = ""
  # Time in minutes

def LoadPlayerData(db, world, wstate):
  data = PlayerData()
  data.selected_item = wstate.getSelectedItem()
  data.chat_who = wstate.getChatCharacter()
  data.status.name = "Traveler"
  data.status.description = "A visitor"
  sleeping = world_state.CharStatus.SLEEPING
  data.status.sleeping = wstate.hasPlayerStatus(sleeping)
  paralized = world_state.CharStatus.PARALIZED
  data.status.paralized = wstate.hasPlayerStatus(paralized)
  poisoned = world_state.CharStatus.POISONED
  data.status.poisoned = wstate.hasPlayerStatus(poisoned)
  brainwashed = world_state.CharStatus.BRAINWASHED
  data.status.brainwashed = wstate.hasPlayerStatus(brainwashed)
  captured = world_state.CharStatus.CAPTURED
  data.status.captured= wstate.hasPlayerStatus(captured)  
  invisible = world_state.CharStatus.INVISIBLE
  data.status.invisible = wstate.hasPlayerStatus(invisible)
  data.status.location = wstate.getLocation()
  data.status.credits = wstate.getPlayerCredits()
  data.status.health = wstate.getPlayerHealthPercent()
  data.status.strength = wstate.getPlayerStrengthPercent()

  for item_id in wstate.getItems():
    item = elements.loadItem(db, item_id)
    if item is None:
      logging.error("unknown item in inventory: %s", item_id)
    else:
      item_info = ElemInfo()
      item_info.id = item_id
      item_info.name = item.getName()
      item_info.description = item.getDescription()
      data.status.inventory.append(item_info)
  
  return data
