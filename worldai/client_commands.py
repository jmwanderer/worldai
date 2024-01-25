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
          response.message = f"Took {item.getName()}"

    elif command.name == CommandName.use:
      item = elements.loadItem(self.db, command.item)
      if item is None:
        response.status.result = StatusCode.error
      elif self.UseItem(item, command.character, response):
        logging.info("use item %s", command.item)
        # TODO: change to result of use
        response.changed = True
      else:
        response.message = f"Unable to use {item.getName()}"

    elif command.name == CommandName.engage:
      character_id = command.character
      character = elements.loadCharacter(self.db, character_id)
      self.wstate.setChatCharacter(character_id)
      logging.info("engage character %s", character_id)
      logging.info("ENGAGE: location: %s", self.wstate.getLocation())   
      response.changed = True
      response.message = f"Talking to {character.getName()}"      


    elif command.name == CommandName.disengage:
      self.wstate.setChatCharacter("")
      logging.info("disengage character")
      response.changed = True
      response.message = f"Talking to nobody"      

    logging.info("Client command response: %s", response.model_dump())
    return response
  

  def UseItem(self, item, cid, response):
    """
    cid is optional
    """
    # May be None
    character = elements.loadCharacter(self.db, cid)

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
    match item.getAbility().effect:
      case elements.ItemEffect.HEAL:
        # Self or other
        if cid is None:
          response.message = "You are healed"
          self.wstate.healPlayer()
        else:
          self.wstate.healCharacter(cid)
          response.message = f"{character.getName()} is healed"
        
      case elements.ItemEffect.HURT:
        # Only other TODO: extend so characters can use
        if cid is not None:
          strength = self.wstate.getCharacterStrength(cid) - 5
          self.wstate.setCharacterStrenth(strength)
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
    
