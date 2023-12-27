from worldai import threads
from worldai import world_state
import unittest
import tempfile
import os
import json
import sqlite3


class BasicTestCase(unittest.TestCase):

  def setUp(self):
    self.dir_name = os.path.dirname(__file__)
    path = os.path.join(self.dir_name, "../worldai/schema.sql")
    self.db = sqlite3.connect("file::memory:",
                              detect_types=sqlite3.PARSE_DECLTYPES)
    self.db.row_factory = sqlite3.Row
    with open(path) as f:
      self.db.executescript(f.read())
    self.user_dir = tempfile.TemporaryDirectory()
    
  def tearDown(self):
    self.db.close()
    self.user_dir.cleanup()

  def testThreads(self):
    thread = "this is binary data"
    session_id = "id_session_1"

    # Simple threads
    self.assertIsNone(threads.get_thread(self.db, session_id))
    threads.save_thread(self.db, session_id, thread)
    result = threads.get_thread(self.db, session_id)
    self.assertEqual(result, thread)
    threads.delete_thread(self.db, session_id)
    self.assertIsNone(threads.get_thread(self.db, session_id))


  def testCharacterThreads(self):
    thread = "this is binary data"
    world_state_id = "id123"
    cid = "id456"

    # Character threads
    self.assertIsNone(threads.get_character_thread(self.db,
                                                   world_state_id,
                                                   cid))

    threads.save_character_thread(self.db, world_state_id, cid, thread)
    result = threads.get_character_thread(self.db,
                                          world_state_id,
                                          cid)
    self.assertEqual(result, thread)    
    threads.delete_character_thread(self.db, world_state_id, cid)
    self.assertIsNone(threads.get_character_thread(self.db,
                                                   world_state_id,
                                                   cid))

  def testWorldState(self):
    session_id = "1234"
    world_id = "ida76"

    state = world_state.loadWorldState(self.db,
                                       session_id, world_id)
    self.assertEqual(state.goal_state, "{}")

    state.goal_state = json.dumps({ "code_words": [ "1" ] })
    world_state.saveWorldState(self.db, state)

    state = world_state.loadWorldState(self.db,
                                       session_id, world_id)
    
    self.assertNotEqual(state.goal_state, "{}")
