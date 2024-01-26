#!/usr/bin/env python3
"""
Represets the state of an instance of a world.
A player interacting with a specific world
"""

# Notes:
# Access to the state strings done through the get_[item|char|site] calls.
# This ensures entries are populated
#
#
# Consider adding an instance ID to the element id
#

import time
import os
import json
import random
import logging
import pydantic
import typing
import enum

from . import elements

PLAYER_ID = "id0"

class CharStatus(str, enum.Enum):
  # Possible states of characters
  SLEEPING ="sleeping"
  PARALIZED = "paralized"
  POISONED = "poisoned"
  BRAINWASHED = "brainwashed"
  CAPTURED = "captured"
  INVISIBLE = "invisible"

class CharState(pydantic.BaseModel):
  """
  Represents state for a instance of a character
  Either a player or an NPC
  """
  location: str = ""
  credits: int = 100
  health: int = 10
  strength: int = 8
  status: typing.List[ CharStatus ] = []

class PlayerState(pydantic.BaseModel):
  friendship: typing.Dict[ str, int] = {}
  chat_who: typing.Optional[str] = None      
  selected_item: typing.Optional[str] = None


class ItemState(pydantic.BaseModel):
  location: str = ""

class SiteState(pydantic.BaseModel):
  locked: bool = False
    
class WorldStateModel(pydantic.BaseModel):
  """
  Represents an instantation of a world
  """
  character_state: typing.Dict[str, CharState] = {}
  player_state: PlayerState = PlayerState()
  item_state: typing.Dict[str, ItemState] = {}
  site_state: typing.Dict[str, SiteState] = {}

class WorldState:
  def __init__(self, wstate_id):
    self.id = wstate_id
    self.session_id = None
    self.world_id = None
    self.model = WorldStateModel()

  def set_model_str(self, str):
    self.model = WorldStateModel(**json.loads(str))

  def get_model_str(self):
    return self.model.model_dump_json()
    
  def get_char(self, char_id):
    if not char_id in self.model.character_state.keys():
      self.model.character_state[char_id] = CharState()
    return self.model.character_state[char_id]

  def get_item(self, item_id):
    if not item_id in self.model.item_state.keys():
      self.model.item_state[item_id] = ItemState()
    return self.model.item_state[item_id]

  def get_site(self, site_id):
    if not site_id in self.model.site_state.keys():
      self.model.site_state[site_id] = SiteState()
    return self.model.site_state[site_id]

  def getCharacterLocation(self, char_id):
    return self.get_char(char_id).location

  def setCharacterLocation(self, char_id, site_id):
    self.get_char(char_id).location = site_id

  def getCharactersAtLocation(self, site_id):
    result = []
    for char_id in self.model.character_state.keys():
      if (char_id != PLAYER_ID and
          self.getCharacterLocation(char_id) == site_id):
        result.append(char_id)
    return result
 
  def setLocation(self, site_id=""):
    self.setCharacterLocation(PLAYER_ID, site_id)

  def getLocation(self):
    return self.getCharacterLocation(PLAYER_ID)

  def getCharacterStrength(self, char_id):
    return self.get_char(char_id).strength

  def setCharacterStrength(self, char_id, value):
    self.get_char(char_id).strength = value

  def getCharacterHealth(self, char_id):
    return self.get_char(char_id).health

  def setCharacterHealth(self, char_id, value):
    self.get_char(char_id).health = value

  def getCharacterCredits(self, char_id):
    return self.get_char(char_id).credits

  def setCharacterCredits(self, char_id, value):
    self.get_char(char_id).credits = value

  def addCharacterStatus(self, char_id, status):
    """
    Add a status to the list of CharStatus
    state: CharStatus
    """
    if not status in self.get_char(char_id).status:
      self.get_char(char_id).status.append(status)

  def removeCharacterStatus(self, char_id, status):
    """
    Remove a status from the list of CharStatus
    state: CharStatus
    """
    if status in self.get_char(char_id).status:
      self.get_char(char_id).status.remove(status)

  def hasCharacterStatus(self, char_id, status):
    logging.info("check character status %s", status)
    logging.info(self.get_char(char_id).status)
    logging.info(status in self.get_char(char_id).status)
    return status in self.get_char(char_id).status

  def addPlayerStatus(self, status):
    self.addCharacterStatus(PLAYER_ID, status)

  def removePlayerStatus(self, status):
    self.removeCharacterStatus(PLAYER_ID, status)

  def hasPlayerStatus(self, status):
    return self.hasCharacterStatus(PLAYER_ID, status)

  def healCharacter(self, char_id):
    self.removeCharacterStatus(char_id, CharStatus.SLEEPING)
    self.removeCharacterStatus(char_id, CharStatus.POISONED)
    self.removeCharacterStatus(char_id, CharStatus.PARALIZED)
    self.removeCharacterStatus(char_id, CharStatus.BRAINWASHED)
    self.setCharacterHealth(char_id, 10)
    self.setCharacterStrength(char_id, 8)

  def healPlayer(self):
    self.healCharacter(PLAYER_ID)
    
  def getPlayerStrength(self):
    return self.getCharacterStrength(PLAYER_ID)

  def setPlayerStrength(self, value):
    self.setCharacterStrength(PLAYER_ID, value)

  def getPlayerHealth(self):
    return self.getCharacterHealth(PLAYER_ID)

  def setPlayerHealth(self, value):
    self.setCharacterHealth(PLAYER_ID, value)

  def getPlayerCredits(self):
    return self.getCharacterCredits(PLAYER_ID)

  def setPlayerCredits(self, value):
    self.setCharacterCredits(PLAYER_ID, value)
    
    
  def getCharacterItems(self, char_id):
    result = []
    for item_id in self.model.item_state.keys():
      if self.model.item_state[item_id].location == char_id:
        result.append(item_id)
    return result

  def addCharacterItem(self, char_id, item_id):
    self.get_item(item_id).location = char_id

  def hasCharacterItem(self, char_id, item_id):
    # True if a character has an item
    return self.get_item(item_id).location == char_id

  def selectItem(self, item_id):
    # mark item as selected by the player. May be empty string
    self.model.player_state.selected_item = item_id

  def getSelectedItem(self):
    return self.model.player_state.selected_item
    
  def addItem(self, item_id):
    # Give an item to the player
    self.get_item(item_id).location = PLAYER_ID

  def hasItem(self, item_id):
    # True if player has this item
    return self.get_item(item_id).location == PLAYER_ID

  def getItems(self):
    # Return a list of item ids possesed by the player
    result = []
    for item_id in self.model.item_state.keys():
      if self.model.item_state[item_id].location == PLAYER_ID:
        result.append(item_id)
    return result

  def setItemLocation(self, item_id, site_id):
    # Set the location of an item
    self.get_item(item_id).location = site_id

  def getItemLocation(self, item_id):
    # Set the location of an item
    return self.get_item(item_id).location

  def getItemsAtLocation(self, site_id):
    # Return list of item_ids at a specific site
    result = []
    for item_id in self.model.item_state.keys():
      if self.model.item_state[item_id].location == site_id:
        result.append(item_id)
    return result

  def increaseFriendship(self, char_id, amount=5):
    level = self.getFriendship(char_id) + amount
    self.model.player_state.friendship[char_id] = level

  def decreaseFriendship(self, char_id, amount=5):
    level = self.getFriendship(char_id) - amount    
    self.model.player_state.friendship[char_id] = level

  def getFriendship(self, char_id):
    if self.model.player_state.friendship.get(char_id) is None:
      return 0
    return self.model.player_state.friendship[char_id]

  def setChatCharacter(self, char_id=None):
    if char_id is None:
      char_id = ""
    self.model.player_state.chat_who = char_id
      
  def getChatCharacter(self):
    """
    Returns character ID or empty string.
    """
    return self.model.player_state.chat_who

  def getSiteLocked(self, site_id):
    """
    Returns True if the site is locked.
    """
    return self.get_site(site_id).locked

  def setSiteLocked(self, site_id, value):
    """
    Record if site is locked
    """
    self.get_site(site_id).locked = value
      

def getWorldStateID(db, session_id, world_id):
  """
  Get an ID for a World State record - create if needed.
  """
  id = None
  initialize = False
  now = time.time()  
  c = db.cursor()  
  c.execute("BEGIN EXCLUSIVE")
  c.execute("SELECT id FROM world_state " +
                 "WHERE session_id = ? and world_id = ?",
                 (session_id, world_id))
  r = c.fetchone()
  if r is None:
    # Insert a record and then populate
    initialize = True
    id = "id%s" % os.urandom(4).hex()
    state = WorldState(id)
    logging.info(f"world id {world_id}")
    c.execute("INSERT INTO world_state (id, session_id, world_id, created, " +
              "updated, state) VALUES (?, ?, ?, ?, ?, ?)",
              (id, session_id, world_id,
               now, now,
               state.get_model_str()))
  else:
    id = r[0]
  db.commit()

  return id


def checkWorldState(db, wstate):
  # Ensure all characters and items are assigned.
  # Initializes everything on first load. Will also
  # set locations for newly added items and characters.
  
  changed = False
  
  characters = elements.listCharacters(db, wstate.world_id)
  sites = elements.listSites(db, wstate.world_id)
  items = elements.listItems(db, wstate.world_id)

  if len(sites) > 0:
    # Assign characters to sites
    for character in characters:
      if wstate.getCharacterLocation(character.getID()) == "":
        site = random.choice(sites)
        wstate.setCharacterLocation(character.getID(), site.getID())
        changed = True
        logging.info("assign %s to location %s",
                     character.getName(),
                     site.getName())

    places = []
    places.extend(characters)
    places.extend(sites)
    if len(characters) > 0 and len(sites) > 0:
      # Set item location - character or site
      for item_entry in items:
        if wstate.model.item_state.get(item_entry.getID()) is None:
          item = elements.loadItem(db, item_entry.getID())
          # Place non-mobile items at sites
          if item.getIsMobile():
            place = random.choice(places)
          else:
            place = random.choice(sites)
          wstate.setItemLocation(item.getID(), place.getID())
          logging.info("place item %s: %s",
                       item.getName(),
                       place.getName())
        changed = True
        
  return changed


def loadWorldState(db, wstate_id):
  """
  Get or create a world state.
  """
  now = time.time()  
  wstate = None
  c = db.cursor()  
  c.execute("SELECT session_id, world_id, state FROM world_state WHERE id = ?",
            (wstate_id,))

  r = c.fetchone()
  if r is not None:
    wstate = WorldState(wstate_id)
    wstate.session_id = r[0]
    wstate.world_id = r[1]
    wstate.set_model_str(r[2])

    if checkWorldState(db, wstate):
      saveWorldState(db, wstate)
    
  return wstate
    

def saveWorldState(db, state):
  """
  Update world state.
  """
  logging.info("world_state: save world state")
  logging.info("location: %s", state.getLocation())  
  now = time.time()
  c = db.cursor()
  c.execute("BEGIN EXCLUSIVE")  
  # Support changing the session_id (Still figuring that out)
  c.execute("UPDATE world_state SET session_id = ?, " +
            "updated = ?, state = ? WHERE id = ?",
            (state.session_id,
             now,
             state.get_model_str(),
             state.id))
  db.commit()
    
