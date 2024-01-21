#!/usr/bin/env python3
"""
Represets the state of an instance of a world.
A player interacting with a specific world
"""

import time
import os
import json
import random
import logging

from . import elements

PROP_CHAR_FRIENDSHIP = "CharacterFriendship"
PROP_CHAT_WHO = "CharacterChat"
PROP_ITEMS = "ItemList"
PLAYER_ID = "id0"

PROP_LOCATION = "Location"
PROP_CREDITS = "Credits"
PROP_HEALTH = "Health"
PROP_STRENGTH = "Strength"



class CharState:
  """
  Represents state for a instance of a character
  Either a player or an NPC
  """
  def __init__(self):
    # Items are recorded under item state
    self.state = { PROP_LOCATION: "",
                   PROP_CREDITS: 100,
                   PROP_HEALTH: 10,
                   PROP_STRENGTH: 8 }

  def getLocation(self):
    return self.state[PROP_LOCATION]

  def setLocation(self, site_id):
    if site_id is None:
      site_id = ""
    self.state[PROP_LOCATION] = site_id

  def getHealth(self):
    return self.state[PROP_HEALTH]

  def setHealth(self, value):
    self.state[PROP_HEALTH] = value

  def getStrength(self):
    return self.state[PROP_STRENGTH]

  def setStrength(self, value):
    self.state[PROP_STRENGTH] = value

  def getCredits(self):
    return self.state[PROP_CREDITS]

  def setCredits(self, value):
    self.state[PROP_CREDITS] = value

  def getStateValue(self):
    return self.state

  def setStateValue(self, value):
    self.state = value
      

    
class WorldState:
  """
  Represents an instantation of a world
  """
  def __init__(self, wstate_id):
    self.id = wstate_id
    self.session_id = None
    self.world_id = None

    self.player_state = { PROP_CHAR_FRIENDSHIP: {},
                          PROP_CHAT_WHO: "",
                         }

    # char_id: CharState   
    self.character_state = {}

    # site_id: { PROP_LOCATION: "" }
    self.item_state = { }

    
  def get_player_state_str(self):
    return json.dumps(self.player_state)

  def set_player_state_str(self, str):
    self.player_state = json.loads(str)

  def get_character_state_str(self):
    # Build a json structure and return a string
    state = {}
    for cid in self.character_state.keys():
      state[cid] = self.character_state[cid].getStateValue()
    return json.dumps(state)

  def set_character_state_str(self, str):
    self.character_state = {}    
    state = json.loads(str)
    for cid in state.keys():
      char_state = CharState()
      char_state.setStateValue(state[cid])
      self.character_state[cid] = char_state
      
  def get_item_state_str(self):
    return json.dumps(self.item_state)

  def set_item_state_str(self, str):
    self.item_state = json.loads(str)

  def get_char(self, char_id):
    if not char_id in self.character_state:
      self.character_state[char_id] = CharState()
    return self.character_state[char_id]

  def get_item(self, item_id):
    if not item_id in self.item_state:
      self.item_state[item_id] = {
        PROP_LOCATION: "" }
    return self.item_state[item_id]

  def getCharacterLocation(self, char_id):
    return self.get_char(char_id).getLocation()

  def setCharacterLocation(self, char_id, site_id):
    self.get_char(char_id).setLocation(site_id)

  def getCharactersAtLocation(self, site_id):
    result = []
    for char_id in self.character_state.keys():
      if self.getCharacterLocation(char_id) == site_id:
        result.append(char_id)
    return result
 
  def setLocation(self, site_id=None):
    self.setCharacterLocation(PLAYER_ID, site_id)

  def getLocation(self):
    return self.getCharacterLocation(PLAYER_ID)

  def getCharacterStrength(self, char_id):
    return self.get_char(char_id).getStrength()

  def setCharacterStrength(self, char_id, value):
    self.get_char(char_id).setStrength(value)

  def getCharacterHealth(self, char_id):
    return self.get_char(char_id).getHealth()

  def setCharacterHealth(self, char_id, value):
    self.get_char(char_id).setHealth(value)

  def getCharacterCredits(self, char_id):
    return self.get_char(char_id).getCredits()

  def setCharacterCredits(self, char_id, value):
    self.get_char(char_id).setCredits(value)

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
    for item_id in self.item_state.keys():
      if self.item_state[item_id][PROP_LOCATION] == char_id:
        result.append(item_id)
    return result

  def addCharacterItem(self, char_id, item_id):
    self.get_item(item_id)[PROP_LOCATION] = char_id

  def hasCharacterItem(self, char_id, item_id):
    # True if a character has an item
    return self.get_item(item_id)[PROP_LOCATION] == char_id

  def addItem(self, item_id):
    # Give an item to the player
    self.get_item(item_id)[PROP_LOCATION] = PLAYER_ID

  def hasItem(self, item_id):
    # True if player has this item
    return self.get_item(item_id)[PROP_LOCATION] == PLAYER_ID

  def getItems(self):
    # Return a list of item ids possesed by the player
    result = []
    for item_id in self.item_state.keys():
      if self.item_state[item_id][PROP_LOCATION] == PLAYER_ID:
        result.append(item_id)
    return result

  def setItemLocation(self, item_id, site_id):
    # Set the location of an item
    self.get_item(item_id)[PROP_LOCATION] = site_id

  def getItemLocation(self, item_id):
    # Set the location of an item
    return self.get_item(item_id)[PROP_LOCATION]

  def getItemsAtLocation(self, site_id):
    # Return list of item_ids at a specific site
    result = []
    for item_id in self.item_state.keys():
      if self.item_state[item_id][PROP_LOCATION] == site_id:
        result.append(item_id)
    return result

  def increaseFriendship(self, char_id, amount=5):
    level = self.getFriendship(char_id) + amount
    self.player_state[PROP_CHAR_FRIENDSHIP][char_id] = level

  def decreaseFriendship(self, char_id, amount=5):
    level = self.getFriendship(char_id) - amount    
    self.player_state[PROP_CHAR_FRIENDSHIP][char_id] = level

  def getFriendship(self, char_id):
    if self.player_state[PROP_CHAR_FRIENDSHIP].get(char_id) is None:
      return 0
    return self.player_state[PROP_CHAR_FRIENDSHIP][char_id]

  def setChatCharacter(self, char_id=None):
    if char_id is None:
      char_id = ""
    self.player_state[PROP_CHAT_WHO] = char_id
      
  def getChatCharacter(self):
    """
    Returns character ID or empty string.
    """
    return self.player_state[PROP_CHAT_WHO]


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
              "updated, player_state, character_state, item_state) " +
              "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (id, session_id, world_id,
               now, now,
               state.get_player_state_str(),
               state.get_character_state_str(),
               state.get_item_state_str()))
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
    if len(places) > 0:
      # Set item location - character or site
      for item in items:
        if wstate.item_state.get(item.getID()) is None:
          place = random.choice(places)
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
  c.execute("SELECT session_id, world_id, player_state, character_state, " +
            "item_state FROM world_state WHERE id = ?",
            (wstate_id,))

  r = c.fetchone()
  if r is not None:
    wstate = WorldState(wstate_id)
    wstate.session_id = r[0]
    wstate.world_id = r[1]
    wstate.set_player_state_str(r[2])
    wstate.set_character_state_str(r[3])
    wstate.set_item_state_str(r[4])    

    if checkWorldState(db, wstate):
      saveWorldState(db, wstate)
    
  return wstate
    

def saveWorldState(db, state):
  """
  Update world state.
  """
  now = time.time()
  c = db.cursor()
  c.execute("BEGIN EXCLUSIVE")  
  # Support changing the session_id (Still figuring that out)
  c.execute("UPDATE world_state SET session_id = ?, " +
            "updated = ?, player_state = ?, character_state = ?, " +
            "item_state = ? WHERE id = ?",
            (state.session_id,
             now,
             state.get_player_state_str(),
             state.get_character_state_str(),
             state.get_item_state_str(),
             state.id))
  db.commit()
    
