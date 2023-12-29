#!/usr/bin/env python3
"""
Represets the state of an instance of a world.
A player interacting with a specific world
"""

import time
import os
import json

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
    self.goal_state = { PROP_CHAR_SUPPORT: [],
                        PROP_LOCATION: "",
                        PROP_CHAT_WHO: "",
                        PROP_ITEMS: []
                       }

  def get_goal_state_str(self):
    return json.dumps(self.goal_state)

  def set_goal_state_str(self, str):
    self.goal_state = json.loads(str)

  def markCharacterSupport(self, char_id):
    if not char_id in self.goal_state[PROP_CHAR_SUPPORT]:
      self.goal_state[PROP_CHAR_SUPPORT].append(char_id)

  def hasCharacterSupport(self, char_id):
    if char_id in self.goal_state[PROP_CHAR_SUPPORT]:
      return True
    return False

  def addItem(self, item_id):
    if not item_id in self.goal_state[PROP_ITEMS]:
      self.goal_state[PROP_ITEMS].append(item_id)
      return True
    return False

  def removeItem(self, item_id):
    if item_id in self.goal_state[PROP_ITEMS]:
      self.goal_state[PROP_ITEMS].remove(item_id)
      return True
    return False

  def setChatCharacter(self, char_id=None):
    if char_id is None:
      char_id = ""
    self.goal_state[PROP_CHAT_WHO] = char_id
      
  def getChatCharacter(self):
    """
    Returns character ID or empty string.
    """
    return self.goal_state[PROP_CHAT_WHO]

  def setLocation(self, site_id=None):
    if site_id is None:
      site_id = ""
    self.goal_state[PROP_LOCATION] = site_id

  def getLocation(self):
    return self.goal_state[PROP_LOCATION]

  def updateGoalState(self, db):
    # pass TODO
    pass


def getWorldStateID(db, session_id, world_id):
  """
  Get an ID for a World State record - create if needed.
  """
  id = None
  now = time.time()  
  c = db.cursor()  
  c.execute("BEGIN EXCLUSIVE")
  c.execute("SELECT id FROM world_state " +
                 "WHERE session_id = ? and world_id = ?",
                 (session_id, world_id))
  r = c.fetchone()
  if r is None:
    id = "id%s" % os.urandom(4).hex()
    state = WorldState(id)
    c.execute("INSERT INTO world_state (id, session_id, world_id, created, " +
              "updated, goal_state) VALUES (?, ?, ?, ?, ?, ?)",
              (id, session_id, world_id,
               now, now, state.get_goal_state_str()))
  else:
    id = r[0]
  db.commit()    
  return id

  
def loadWorldState(db, wstate_id):
  """
  Get or create a world state.
  """
  now = time.time()  
  state = None
  c = db.cursor()  
  c.execute("SELECT session_id, world_id, goal_state FROM world_state " +
                 "WHERE id = ?",
                 (wstate_id,))

  r = c.fetchone()
  if r is not None:
    state = WorldState(wstate_id)
    state.session_id = r[0]
    state.world_id = r[1]
    state.set_goal_state_str(r[2])
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
            "updated = ?, goal_state = ? WHERE id = ?",
            (state.session_id,  now, state.get_goal_state_str(), state.id))
  db.commit()
    
