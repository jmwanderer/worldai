"""
Implements the game play commands.
"""
import logging
import pydantic
import typing
import enum


from . import elements
from . import world_state

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

# TODO: create a command response
  

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

    changed = False
    ok = { "status": "ok" }
    result = { "status": "error" }

    if command.name == CommandName.go:
      site_id = command.to
      # Verify location
      site = elements.loadSite(self.db, site_id)
      if site is not None:
        self.wstate.setLocation(site_id)
        logging.info("GO: set location %s",  site_id)
      else:
        self.wstate.setLocation("")
        logging.info("GO: clear location")        
      changed = True
      result = ok

    elif command.name == CommandName.take:
      item_id = command.item
      logging.info("take item %s", item_id)
      
      # Verify 
      if self.wstate.getItemLocation(item_id) == self.wstate.getLocation():
        item = elements.loadItem(self.db, item_id)
        if item.getIsMobile():
          self.wstate.addItem(item_id)
          changed = True
        result = ok

    elif command.name == CommandName.use:
      if self.UseItem(command.item, command.character):
        logging.info("use item %s", command.item)
        result = ok
        changed = True

    elif command.name == CommandName.engage:
      character_id = command.character
      self.wstate.setChatCharacter(character_id)
      logging.info("engage character %s", character_id)
      logging.info("ENGAGE: location: %s", self.wstate.getLocation())   
      changed = True      
      result = ok

    elif command.name == CommandName.disengage:
      self.wstate.setChatCharacter("")
      logging.info("disengage character")
      changed = True      
      result = ok

    return result, changed
  

  def UseItem(self, item_id, cid):
    """
    cid is optional
    """
    # Verify the use can access the item 
    item = elements.loadItem(self.db, item_id)
    if item.getIsMobile():
      # Verify user has the item
      if not wstate.hasItem(item_id):
        return False
    else:
      # Verify same location
      if self.wstate.getItemLocation(item_id) != self.wstate.getLocation():
        return False

    sleeping = world_state.CharStatus.SLEEPING
    poisoned = world_state.CharStatus.POISONED
    paralized = world_state.CharStatus.PARALIZED
    brainwashed = world_state.CharStatus.BRAINWASHED
    captured = world_state.CharStatus.CAPTURED
    invisible = world_state.CharStatus.INVISIBLE
    
    # Item my act on player, a character, or something else
    match item.getAbility().action:
      case elements.ItemAction.APPLY:
        logging.info("use item - apply %s", item.getAbility().effect)
        # Apply an effect
        match item.getAbility().effect:
          case elements.ItemEffect.SLEEP:
            if cid is None:
              self.wstate.addPlayerStatus(sleeping)
            else:
              self.wstate.addCharacterStatus(cid, sleeping)
              
          case elements.ItemEffect.PARALIZE:
            if cid is None:
              self.wstate.addPlayerStatus(paralized)
            else:
              self.wstate.addCharacterStatus(cid, paralized)
            
          case elements.ItemEffect.POISON:
            logging.info("poison")
            if cid is None:
              logging.info("poison player")
              self.wstate.addPlayerStatus(poisoned)
            else:
              self.wstate.addCharacterStatus(cid, poisoned)
            
          case elements.ItemEffect.BRAINWASH:
            if cid is None:
              self.wstate.addPlayerStatus(brainwashed)
            else:
              self.wstate.addCharacterStatus(cid, brainwashed)
            
          case elements.ItemEffect.CAPTURE:
            if cid is None:
              self.wstate.addPlayerStatus(captured)
            else:
              self.wstate.addCharacterStatus(cid, captured)
            
          case elements.ItemEffect.INVISIBLE:
            if cid is None:
              self.wstate.addPlayerStatus(invisible)
            else:
              self.wstate.addCharacterStatus(cid, invisible)
            
          case elements.ItemEffect.KILL:
            if cid is None:
              self.wstate.setPlayerHealth(0)
            else:
              self.wstate.setCharacterHealth(cid, 0)
            
          case elements.ItemEffect.LOCK:
            pass
        
      case elements.ItemAction.CLEAR:
        pass

      case elements.ItemAction.TOGGLE:
        pass

    return True
    
