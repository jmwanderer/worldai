"""
Implements the game play commands.
"""
import logging

class ClientActions:
  def __init__(self, world, wstate):
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

    if (command.get("name") == "go"):
      site_id = command.get("to")
      # Verify location
      site = elements.loadSite(get_db(), site_id)
      if site is not None:
        self.wstate.setLocation(site_id)
      else:
        self.wstate.setLocation(None)      
      changed = True
      result = ok

    elif (command.get("name") == "take"):
      item_id = command.get("item")
      # Verify 
      if self.wstate.getItemLocation(item_id) == wstate.getLocation():
        self.wstate.addItem(item_id)
        changed = True
        result = ok

    elif (command.get("name") == "engage"):
      character_id = command.get("character")
      self.wstate.setChatCharacter(character_id)
      logging.info("engage character %s", character_id)
      changed = True      
      result = ok

    elif (command.get("name") == "disengage"):
      self.wstate.setChatCharacter(None)
      logging.info("disengage character")
      changed = True      
      result = ok

    return result, changed
  

    
