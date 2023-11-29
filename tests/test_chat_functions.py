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
    chat_functions.InitializeStateVars()
    
  def tearDown(self):
    self.db.close()
    self.user_dir.cleanup()

  def test_exec_calls_world(self):
    func_call = { 'name': 'CreateWorld',
                  'arguments': '{ "name": "world 2" }' }
    self.assertCallAvailable('CreateWorld')
    id2 = chat_functions.execute_function_call(func_call)
    id2 = json.loads(id2)        
    self.assertIsNotNone(id2)

    self.callFunction('ChangeState', '{ "state": "State_Worlds" }')
    
    func_call = { 'name': 'CreateWorld',
                  'arguments': '{ "name": "world 1" }' }
    self.assertCallAvailable('CreateWorld')
    id1 = chat_functions.execute_function_call(func_call)
    id1 = json.loads(id1)    
    self.assertIsNotNone(id1)


    self.callFunction('ChangeState', '{ "state": "State_Worlds" }')
    
    func_call = { 'name': 'ListWorlds',
                  'arguments': '{}' }
    self.assertCallAvailable('ListWorlds')
    content = chat_functions.execute_function_call(func_call)
    values = json.loads(content)
    self.assertEqual(len(values), 2)
    self.assertEqual(values[0]["id"], id2)
    self.assertEqual(values[1]["id"], id1)

    func_call = { 'name': 'ReadWorld',
                  'arguments':
                  ('{ "id": "%s" }' % id1)}
    self.assertCallAvailable('ReadWorld')
    content = chat_functions.execute_function_call(func_call)
    values = json.loads(content)    
    self.assertIsNone(values.get("details"))

    self.callFunction('ChangeState', '{ "state": "State_Edit_World" }')    
    
    func_call = { 'name': 'UpdateWorld',
                  'arguments':
                  '{ "name": "world 1", ' +
                  ' "description": "a description", ' +
                  ' "details": "details" }' }
    self.assertCallAvailable('UpdateWorld')                  
    chat_functions.execute_function_call(func_call)

    func_call = { 'name': 'ReadWorld',
                  'arguments':
                  ('{ "id": "%s" }' % id1)}
    self.assertCallAvailable('ReadWorld')
    content = chat_functions.execute_function_call(func_call)
    values = json.loads(content)    
    self.assertEqual(values["details"], "details")
    
  def test_available_functions(self):
    # STATE_WORLDS
    functions = chat_functions.get_available_functions()
    self.assertEqual(len(functions), 3)
    self.assertCallAvailable('ListWorlds')
    self.assertCallNotAvailable('UpdateWorld')    
    self.assertIsNotNone(chat_functions.get_state_instructions())
    self.assertIn("new world", chat_functions.get_state_instructions())
                       
    self.callFunction('CreateWorld', '{ "name": "world 1" }')

    # STATE EDIT WORLD
    self.assertEqual(chat_functions.current_state,
                     chat_functions.STATE_EDIT_WORLD)
    self.assertCallAvailable('UpdateWorld')    
    self.assertCallNotAvailable('ListWorlds')
    self.assertIsNotNone(chat_functions.get_state_instructions())
    self.assertIn("description", chat_functions.get_state_instructions())
    self.callFunction('ChangeState', '{ "state": "State_View_World" }')

    # STATE VIEW WORLD
    self.assertEqual(chat_functions.current_state,
                     chat_functions.STATE_VIEW_WORLD)
    self.callFunction('ChangeState', '{ "state": "State_Edit_Characters" }')

    # STATE EDIT CHARACTERS
    self.assertEqual(chat_functions.current_state,
                     chat_functions.STATE_EDIT_CHARACTERS)
    self.assertCallNotAvailable('UpdateWorld')
    self.assertCallAvailable('ListCharacters')
    self.assertCallAvailable('CreateCharacter')
    self.assertCallAvailable('ReadCharacter')

    id = self.callFunction('CreateCharacter','{ "name": "char 1" }')
    id = json.loads(id)

    # STATE EDIT CHARACTER
    self.assertEqual(chat_functions.current_state,
                     chat_functions.STATE_EDIT_CHARACTERS)
    self.assertCallAvailable('UpdateCharacter')

    self.callFunction('UpdateCharacter',
                      '{ "id": "' + id + '", "name": "my char 1", ' +
                      ' "description": "a description", ' +
                      ' "details": "my details" }')

    content = self.callFunction('ReadCharacter',
                                '{ "id": "' + id + '" }')
    print(content)
    values = json.loads(content)    
    self.assertEqual(values["details"], "my details")
    self.assertEqual(values["name"], "my char 1")

    self.callFunction('ChangeState', '{ "state": "State_View_World" }')    
    self.assertEqual(chat_functions.current_state,
                     chat_functions.STATE_VIEW_WORLD)
    
    
  
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
    
