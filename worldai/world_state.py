#!/usr/bin/env python3
"""
Represets the state of an instance of a world.
A player interacting with a specific world
"""

import time
import os
import json

class WorldState:
  """
  Represents an instantation of a world
  """
  def __init__(self, wstate_id):
    self.id = wstate_id
    self.session_id = None
    self.world_id = None
    self.goal_state = "{}"


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
    state.goal_state = r[2]
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
            (state.session_id,  now, state.goal_state, state.id))
  db.commit()
    
