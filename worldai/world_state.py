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
  def __init__(self, session_id, world_id):
    self.id = None
    self.session_id = session_id    
    self.world_id = world_id
    self.goal_state = "{}"


def loadWorldState(db, session_id, world_id):
  """
  Get or create a world state.
  """
  now = time.time()  
  state = WorldState(session_id, world_id)
  c = db.cursor()  
  c.execute("BEGIN EXCLUSIVE")
  c.execute("SELECT id, goal_state FROM world_state " +
                 "WHERE session_id = ? and world_id = ?",
                 (session_id, world_id))
  r = c.fetchone()
  if r is None:
    state.id = "id%s" % os.urandom(4).hex()
    c.execute("INSERT INTO world_state (id, session_id, world_id, created, " +
              "updated, goal_state) VALUES (?, ?, ?, ?, ?, ?)",
              (state.id, state.session_id, state.world_id,
               now, now, state.goal_state))
  else:
    state.id = r[0]
    state.goal_state = r[1]
  db.commit()    
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
    
