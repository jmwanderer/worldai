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
    self.assertEqual(values[0]["world_id"], 1)
    self.assertEqual(values[1]["world_id"], 2)    
    
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
    
  def test_available_functions(self):
    # STATE_WORLDS
    functions = chat_functions.get_available_functions()
    self.assertEqual(len(functions), 3)
    self.assertCallAvailable('list_worlds')
    self.assertCallNotAvailable('update_world')    

    self.callFunction('create_world', '{ "name": "world 1" }')

    # STATE EDIT WORLD
    self.assertEqual(chat_functions.current_state,
                     chat_functions.STATE_EDIT_WORLD)
    self.assertCallAvailable('update_world')    
    self.assertCallNotAvailable('list_worlds')

    self.callFunction('open_characters', '{ }')

    # STATE CHARACTERS
    self.assertCallNotAvailable('update_world')
    self.assertCallAvailable('list_characters')
    self.assertCallAvailable('create_character')
    self.assertCallAvailable('read_character')

    id = self.callFunction('create_character','{ "name": "char 1" }')
    # STATE CHARACTER
    self.assertCallNotAvailable('list_characters')
    self.assertCallAvailable('update_character')

    self.callFunction('update_character',
                      '{ "id": "' + id + '", "name": "my char 1", ' +
                      ' "description": "a description", ' +
                      ' "details": "my details" }')

    content = self.callFunction('read_character',
                                '{ "id": "' + id + '" }')
    print(content)
    values = json.loads(content)    
    self.assertEqual(values["details"], "my details")
    self.assertEqual(values["name"], "my char 1")
    
    
  
  def assertCallAvailable(self, name):
    # Assert we are allowed to call the function in the current state    
    functions = chat_functions.get_available_functions()
    names = [ x["name"] for x in functions ]
    self.assertIn(name, names)

  def assertCallNotAvailable(self, name):
    # Assert we are allowed to call the function in the current state    
    functions = chat_functions.get_available_functions()
    names = [ x["name"] for x in functions ]
    self.assertNotIn(name, names)

  def callFunction(self, name, arguments):
    """
    Invoke the execute_function_call
    name: string name of function call
    arguments: json string of arguments
    """
    # Assert we are allowed to call it in the current state
    self.assertCallAvailable(name)
    func_call = { 'name': name,
                  'arguments': arguments }
    return chat_functions.execute_function_call(func_call)
    
if __name__ ==  '__main__':
  unittest.main()
    
