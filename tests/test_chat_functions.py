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
    self.chatFunctions = chat_functions.ChatFunctions()
    
  def tearDown(self):
    self.db.close()
    self.user_dir.cleanup()

  def test_exec_calls_world(self):
    self.assertCallAvailable('CreateWorld')
    id2 = self.callFunction('CreateWorld',
                            '{ "name": "world 2" }')
    id2 = json.loads(id2)        
    self.assertIsNotNone(id2)

    self.callFunction('ChangeState', '{ "state": "State_Worlds" }')
    
    self.assertCallAvailable('CreateWorld')
    id1 = self.callFunction('CreateWorld', '{ "name": "world 1" }')
    id1 = json.loads(id1)    
    self.assertIsNotNone(id1)


    self.callFunction('ChangeState', '{ "state": "State_Worlds" }')
    
    self.assertCallAvailable('ListWorlds')
    content = self.callFunction('ListWorlds', '{}')
    values = json.loads(content)
    self.assertEqual(len(values), 2)
    self.assertEqual(values[0]["id"], id2)
    self.assertEqual(values[1]["id"], id1)

                  
    self.assertCallAvailable('ReadWorld')
    content = self.callFunction('ReadWorld', '{ "id": "%s" }' % id1)
    values = json.loads(content)    
    self.assertIsNone(values.get("details"))

    self.callFunction('ChangeState', '{ "state": "State_Edit_World" }')    
    
    self.assertCallAvailable('UpdateWorld')                  
    self.callFunction('UpdateWorld',
                      '{ "name": "world 1", ' +
                      ' "description": "a description", ' +
                      ' "details": "details" }')
    
    self.assertCallAvailable('ReadWorld')
    content = self.callFunction('ReadWorld', '{ "id": "%s" }' % id1)
    values = json.loads(content)    
    self.assertEqual(values["details"], "details")
    
  def test_available_functions(self):
    # STATE_WORLDS
    functions = self.chatFunctions.get_available_tools()
    self.assertEqual(len(functions), 3)
    self.assertCallAvailable('ListWorlds')
    self.assertCallNotAvailable('UpdateWorld')    
    self.assertIsNotNone(self.chatFunctions.get_state_instructions())
    self.assertIn("new world", self.chatFunctions.get_state_instructions())
                       
    self.callFunction('CreateWorld', '{ "name": "world 1" }')

    # STATE EDIT WORLD
    self.assertEqual(self.chatFunctions.current_state,
                     chat_functions.STATE_EDIT_WORLD)
    self.assertCallAvailable('UpdateWorld')    
    self.assertCallNotAvailable('ListWorlds')
    self.assertIsNotNone(self.chatFunctions.get_state_instructions())
    self.assertIn("description", self.chatFunctions.get_state_instructions())
    self.callFunction('ChangeState', '{ "state": "State_View_World" }')

    # STATE VIEW WORLD
    self.assertEqual(self.chatFunctions.current_state,
                     chat_functions.STATE_VIEW_WORLD)
    self.callFunction('ChangeState', '{ "state": "State_Edit_Characters" }')

    # STATE EDIT CHARACTERS
    self.assertEqual(self.chatFunctions.current_state,
                     chat_functions.STATE_EDIT_CHARACTERS)
    self.assertCallNotAvailable('UpdateWorld')
    self.assertCallAvailable('ListCharacters')
    self.assertCallAvailable('CreateCharacter')
    self.assertCallAvailable('ReadCharacter')

    id = self.callFunction('CreateCharacter','{ "name": "char 1" }')
    id = json.loads(id)

    # STATE EDIT CHARACTER
    self.assertEqual(self.chatFunctions.current_state,
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
    self.assertEqual(self.chatFunctions.current_state,
                     chat_functions.STATE_VIEW_WORLD)
    
    
  
  def assertCallAvailable(self, name):
    # Assert we are allowed to call the function in the current state    
    functions = self.chatFunctions.get_available_tools()
    names = [ x["function"]["name"] for x in functions ]
    self.assertIn(name, names)

  def assertCallNotAvailable(self, name):
    # Assert we are allowed to call the function in the current state    
    functions = self.chatFunctions.get_available_tools()
    names = [ x["function"]["name"] for x in functions ]
    self.assertNotIn(name, names)

  def callFunction(self, name, arguments):
    """
    Invoke the execute_function_call
    name: string name of function call
    arguments: json string of arguments
    """
    # Assert we are allowed to call it in the current state
    self.assertCallAvailable(name)
    args = json.loads(arguments)
    return self.chatFunctions.execute_function_call(self.db, name, args)
    
if __name__ ==  '__main__':
  unittest.main()
    
