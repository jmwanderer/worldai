"""
Implements the game play commands.
"""
import logging
import pydantic
import typing
import enum

from . import elements

class CommandName(str, enum.Enum):
  go = 'go'
  take = 'take'
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
      # Verify 
      if self.wstate.getItemLocation(item_id) == self.wstate.getLocation():
        item = elements.loadItem(self.db, item_id)
        if item.getIsMobile():
          self.wstate.addItem(item_id)
          changed = True
        result = ok

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
  

    
