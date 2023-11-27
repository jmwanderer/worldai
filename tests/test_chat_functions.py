from worldai import elements
from worldai import chat_functions

import unittest
import tempfile
import os
import sqlite3
import json


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
    chat_functions.debug_set_db(self.db)
    
  def tearDown(self):
    self.db.close()
    self.user_dir.cleanup()

  def test_exec_calls_world(self):
    func_call = { 'name': 'create_world',
                  'arguments': '{ "name": "world 1" }' }
    val = chat_functions.execute_function_call(func_call)
    self.assertEqual(val, "1")

    func_call = { 'name': 'create_world',
                  'arguments': '{ "name": "world 2" }' }
    val = chat_functions.execute_function_call(func_call)
    self.assertEqual(val, "2")

    func_call = { 'name': 'list_worlds',
                  'arguments': '{}' }
    content = chat_functions.execute_function_call(func_call)
    values = json.loads(content)
    self.assertEqual(len(values), 2)
    self.assertEqual(values[0]["id"], 1)
    self.assertEqual(values[1]["id"], 2)    
    
    func_call = { 'name': 'update_world',
                  'arguments':
                  '{ "world_id": "1", "name": "world 1", ' +
                  ' "description": "a description", ' +
                  ' "details": "details" }' }
                  
    chat_functions.execute_function_call(func_call)

    func_call = { 'name': 'read_world',
                  'arguments':
                  '{ "world_id": "1" }'}
    content = chat_functions.execute_function_call(func_call)
    values = json.loads(content)    
    self.assertEqual(values["details"], "details")
    

if __name__ ==  '__main__':
  unittest.main()
    
