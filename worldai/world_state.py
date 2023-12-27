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
  state = WorldState(session_id, world_id)
    
  q = db.execute("SELECT id, goal_state FROM world_state " +
                 "WHERE session_id = ? and world_id = ?",
                 (session_id, world_id))
  r = q.fetchone()
  if r is None:
    state.id = "id%s" % os.urandom(4).hex()
  else:
    state.id = r[0]
    state.goal_state = r[1]
  return state
    

def saveWorldState(db, state):
  """
  Save world state. May create or update.
  """
  now = time.time()
  c = db.cursor()
  c.execute("BEGIN EXCLUSIVE")
  c.execute("SELECT id FROM world_state WHERE session_id = ? AND world_id = ?",
            (state.session_id, state.world_id))
  r = c.fetchone()
  if r is None:
    # INSERT
    c.execute("INSERT INTO world_state (id, session_id, world_id, created, " +
              "updated, goal_state) VALUES (?, ?, ?, ?, ?, ?)",
              (state.id, state.session_id, state.world_id,
               now, now, state.goal_state))
  else:
    # UPDATE
    # Support changing the session_id (Still figuring that out)
    c.execute("UPDATE world_state SET session_id = ?, " +
              "updated = ?, goal_state = ? WHERE id = ?",
              (state.session_id,  now, state.goal_state, state.id))
  db.commit()
    
