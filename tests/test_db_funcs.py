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
    wstate_id = "xxx"
    char_id = "id123"
    item_id = "id456"
    site_id = "id789"            

    state = world_state.loadWorldState(self.db, wstate_id)
    self.assertIsNone(state)

    wstate_id = world_state.getWorldStateID(self.db, session_id, world_id)
    state = world_state.loadWorldState(self.db, wstate_id)
    self.assertIsNotNone(state)

    self.assertEqual(len(state.player_state[world_state.PROP_CHAR_SUPPORT]), 0)
    self.assertFalse(state.hasCharacterSupport(char_id))

    state.markCharacterSupport(char_id)
    self.assertTrue(state.hasCharacterSupport(char_id))

    self.assertEqual(len(state.getChatCharacter()), 0)
    state.setChatCharacter(char_id)

    self.assertEqual(len(state.getItems()), 0)
    state.addItem(item_id)
    self.assertTrue(state.hasItem(item_id))
    self.assertEqual(len(state.getItems()), 1)

    self.assertEqual(len(state.getLocation()), 0)    
    state.setLocation(site_id)

    state.setCharacterLocation(char_id, site_id)

    self.assertEqual(site_id, state.getCharacterLocation(char_id))

    state.addCharacterItem(char_id, item_id)
    self.assertEqual(1, len(state.getCharacterItems(char_id)))
    self.assertTrue(state.hasCharacterItem(char_id, item_id))    

    state.setItemLocation(item_id, site_id)
    self.assertEqual(1, len(state.getItemsAtLocation(site_id)))    

    state.addItem(item_id)    
    world_state.saveWorldState(self.db, state)

    state = world_state.loadWorldState(self.db, wstate_id)
    self.assertTrue(state.hasCharacterSupport(char_id))
    self.assertEqual(len(state.getItems()), 1)
    self.assertNotEqual(len(state.getLocation()), 0)
    self.assertNotEqual(len(state.getChatCharacter()), 0) 

    self.assertEqual(site_id, state.getCharacterLocation(char_id))
