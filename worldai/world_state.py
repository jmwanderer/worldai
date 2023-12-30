#!/usr/bin/env python3
"""
Represets the state of an instance of a world.
A player interacting with a specific world
"""

import time
import os
import json
import random

from . import elements

PROP_CHAR_SUPPORT = "CharacterSupport"
PROP_LOCATION = "Location"
PROP_CHAT_WHO = "CharacterChat"
PROP_ITEMS = "ItemList"

class WorldState:
  """
  Represents an instantation of a world
  """
  def __init__(self, wstate_id):
    self.id = wstate_id
    self.session_id = None
    self.world_id = None
    # TODO: conisder splitting this up
    self.player_state = { PROP_CHAR_SUPPORT: [],
                          PROP_LOCATION: "",
                          PROP_CHAT_WHO: "",
                          PROP_ITEMS: []
                         }

    self.character_state = { }
    # char_id: { PROP_LOCATION: "",
    #            PROP_ITEMS: [] }
    

  def get_player_state_str(self):
    return json.dumps(self.player_state)

  def set_player_state_str(self, str):
    self.player_state = json.loads(str)

  def get_character_state_str(self):
    return json.dumps(self.character_state)

  def set_character_state_str(self, str):
    self.character_state = json.loads(str)

  def get_char(self, char_id):
    if not char_id in self.character_state:
      self.character_state[char_id] = {
        PROP_LOCATION: "",
        PROP_ITEMS: [] }
    return self.character_state[char_id]

  def getCharacterLocation(self, char_id):
    return self.get_char(char_id)[PROP_LOCATION]

  def setCharacterLocation(self, char_id, site_id):
    self.get_char(char_id)[PROP_LOCATION] = site_id    

  def getCharacterItems(self, char_id):
    return self.get_char(char_id)[PROP_ITEMS]

  def addCharacterItem(self, char_id, item_id):
    if item_id not in self.get_char(char_id)[PROP_ITEMS]:
      self.get_char(char_id)[PROP_ITEMS].append(item_id)
      return True
    return False

  def removeCharacterItem(self, char_id, item_id):
    if item_id in self.get_char(char_id)[PROP_ITEMS]:
      self.get_char(char_id)[PROP_ITEMS].remove(item_id)
      return True
    return False

  def markCharacterSupport(self, char_id):
    if not char_id in self.player_state[PROP_CHAR_SUPPORT]:
      self.player_state[PROP_CHAR_SUPPORT].append(char_id)

  def hasCharacterSupport(self, char_id):
    if char_id in self.player_state[PROP_CHAR_SUPPORT]:
      return True
    return False

  def addItem(self, item_id):
    if not item_id in self.player_state[PROP_ITEMS]:
      self.player_state[PROP_ITEMS].append(item_id)
      return True
    return False

  def removeItem(self, item_id):
    if item_id in self.player_state[PROP_ITEMS]:
      self.player_state[PROP_ITEMS].remove(item_id)
      return True
    return False

  def getItems(self):
    return self.player_state[PROP_ITEMS]

  def setChatCharacter(self, char_id=None):
    if char_id is None:
      char_id = ""
    self.player_state[PROP_CHAT_WHO] = char_id
      
  def getChatCharacter(self):
    """
    Returns character ID or empty string.
    """
    return self.player_state[PROP_CHAT_WHO]

  def setLocation(self, site_id=None):
    if site_id is None:
      site_id = ""
    self.player_state[PROP_LOCATION] = site_id

  def getLocation(self):
    return self.player_state[PROP_LOCATION]

  def updateGoalState(self, db):
    # pass TODO
    pass


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
    c.execute("INSERT INTO world_state (id, session_id, world_id, created, " +
              "updated, player_state, character_state) " +
              "VALUES (?, ?, ?, ?, ?, ?, ?)",
              (id, session_id, world_id,
               now, now,
               state.get_player_state_str(),
               state.get_character_state_str()))
  else:
    id = r[0]
  db.commit()

  if initialize:
    wstate = initializeWorldState(db, id)
    if wstate is not None:
      saveWorldState(db, wstate)
  return id

def initializeWorldState(db, wstate_id):
  # Setup locations and item assignments.
  wstate = loadWorldState(db, wstate_id)
  if wstate is None:
    return None

  characters = elements.listCharacters(db, wstate.world_id)
  sites = elements.listSites(db, wstate.world_id)
  items = elements.listItems(db, wstate.world_id)

  if len(sites) > 0:
    # Assign characters to sites
    for character in characters:
      site = random.choice(sites)
      wstate.setCharacterLocation(character.getID(), site.getID())
      print("assign %s to location %s" % (character.getName(),
                                          site.getName()))

    site = random.choice(sites)
    wstate.setLocation(site.getID())    
    print("assign player to location %s" % site.getName())
    
  if len(characters) > 0:
    # Assign items to characters
    for item in items:
      character = random.choice(characters)      
      wstate.addCharacterItem(character.getID(), item.getID())
      print("give item %s to %s" % (item.getName(), character.getName()))
  return wstate
  
  
def loadWorldState(db, wstate_id):
  """
  Get or create a world state.
  """
  now = time.time()  
  state = None
  c = db.cursor()  
  c.execute("SELECT session_id, world_id, player_state, character_state " +
            "FROM world_state WHERE id = ?",
            (wstate_id,))

  r = c.fetchone()
  if r is not None:
    state = WorldState(wstate_id)
    state.session_id = r[0]
    state.world_id = r[1]
    state.set_player_state_str(r[2])
    state.set_character_state_str(r[3])    
  return state
    

def saveWorldState(db, state):
  """
  Update world state.
  """
  now = time.time()
  c = db.cursor()
  c.execute("BEGIN EXCLUSIVE")  
  # Support changing the session_id (Still figuring that out)
  c.execute("UPDATE world_state SET session_id = ?, " +
            "updated = ?, player_state = ?, character_state = ? WHERE id = ?",
            (state.session_id,
             now,
             state.get_player_state_str(),
             state.get_character_state_str(),             
             state.id))
  db.commit()
    
