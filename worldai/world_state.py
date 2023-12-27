#!/usr/bin/env python3
"""
Represets the state of an instance of a world.
A player interacting with a specific world
"""

import time
import os
import json

PROP_CHAR_CHALLENGE_DONE = "CharacterChallengeDone"

class WorldState:
  """
  Represents an instantation of a world
  """
  def __init__(self, wstate_id):
    self.id = wstate_id
    self.session_id = None
    self.world_id = None
    self.goal_state = {}

  def get_goal_state_str(self):
    return json.dumps(self.goal_state)

  def set_goal_state_str(self, str):
    self.goal_state = json.loads(str)

  def markCharacterChallenge(self, char_id):
    if self.goal_state.get(PROP_CHAR_CHALLENGE_DONE) is None:
      self.goal_state[PROP_CHAR_CHALLENGE_DONE] = []
    if not char_id in self.goal_state[PROP_CHAR_CHALLENGE_DONE]:
      self.goal_state[PROP_CHAR_CHALLENGE_DONE].append(char_id)

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
    c.execute("INSERT INTO world_state (id, session_id, world_id, created, " +
              "updated, goal_state) VALUES (?, ?, ?, ?, ?, ?)",
              (id, session_id, world_id,
               now, now, "{}"))
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
    
