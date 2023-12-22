from worldai import threads
import unittest
import tempfile
import os
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
    wid = "id123"
    cid = "id456"

    # Simple threads
    self.assertIsNone(threads.get_thread(self.db, session_id))
    threads.save_thread(self.db, session_id, thread)
    result = threads.get_thread(self.db, session_id)
    self.assertEqual(result, thread)
    threads.delete_thread(self.db, session_id)
    self.assertIsNone(threads.get_thread(self.db, session_id))

    # Character threads
    self.assertIsNone(threads.get_character_thread(self.db,
                                                   session_id,
                                                   wid,
                                                   cid))
    threads.save_character_thread(self.db, session_id, wid, cid, thread)
    result = threads.get_character_thread(self.db,
                                          session_id,
                                          wid,
                                          cid)
    self.assertEqual(result, thread)    
    threads.delete_character_thread(self.db, session_id, wid, cid)
    self.assertIsNone(threads.get_character_thread(self.db,
                                                   session_id,
                                                   wid,
                                                   cid))
