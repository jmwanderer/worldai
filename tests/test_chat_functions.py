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
    self.db = sqlite3.connect("file::memory:")
    with open(path) as f:
      self.db.executescript(f.read())
    self.user_dir = tempfile.TemporaryDirectory()
    self.chatFunctions = chat_functions.ChatFunctions()
    
  def tearDown(self):
    self.db.close()
    self.user_dir.cleanup()

  def test_token_tracking(self):
    chat_functions.track_tokens(self.db, 1, 100, 100, 100)
    chat_functions.count_image(self.db, 1, 1)
    self.assertTrue(chat_functions.check_token_budgets(self.db))
    self.assertTrue(chat_functions.check_image_budget(self.db))    

    chat_functions.track_tokens(self.db, 2, 100, 100, 100)
    chat_functions.count_image(self.db, 2, 1)

    self.assertTrue(chat_functions.check_token_budgets(self.db))
    self.assertTrue(chat_functions.check_image_budget(self.db))    

    # Add a budget
    self.db.execute("INSERT INTO token_usage VALUES (?, 500, 500, 500, 5)",
                    ("limits",))
    self.db.commit()
    self.assertTrue(chat_functions.check_token_budgets(self.db))
    self.assertTrue(chat_functions.check_image_budget(self.db))

    chat_functions.track_tokens(self.db, 1, 300, 300, 300)
    chat_functions.count_image(self.db, 1, 3)

    self.assertFalse(chat_functions.check_token_budgets(self.db))
    self.assertFalse(chat_functions.check_image_budget(self.db))

    

  def test_exec_calls_world(self):
    self.assertCallAvailable('CreateWorld')
    result = self.callFunction('CreateWorld',
                               '{ "name": "world 2" }')
    id2 = result["id"]
    self.assertIsNotNone(id2)

    # Check illegal state
    result = self.callFunction('ChangeState', '{ "state": "non existent" }')
    self.assertIsNotNone(result.get("error"))
    
    self.callFunction('ChangeState', '{ "state": "State_Worlds" }')
    
    self.assertCallAvailable('CreateWorld')
    result = self.callFunction('CreateWorld', '{ "name": "world 1" }')
    id1 = result["id"]
    self.assertIsNotNone(id1)

    self.callFunction('ChangeState', '{ "state": "State_Worlds" }')    

    # Create duplicate name
    result = self.callFunction('CreateWorld', '{ "name": "world 1" }')
    self.assertIsNotNone(result.get("error"))
    
    self.assertCallAvailable('ListWorlds')
    values = self.callFunction('ListWorlds', '{}')
    self.assertEqual(len(values), 2)
    self.assertEqual(values[0]["id"], id2)
    self.assertEqual(values[1]["id"], id1)

    # Read not existent world
    values = self.callFunction('ReadWorld', '{ "id": "not_exist" }')
    self.assertIsNotNone(values.get("error"))
                  
    self.assertCallAvailable('ReadWorld')
    values = self.callFunction('ReadWorld', '{ "id": "%s" }' % id1)
    self.assertIsNone(values.get("details"))

    self.callFunction('ChangeState', '{ "state": "State_Edit_World" }')    
    
    self.assertCallAvailable('UpdateWorld')                  
    self.callFunction('UpdateWorld',
                      '{ "name": "world 1", ' +
                      ' "description": "a description", ' +
                      ' "details": "details" }')
    
    self.assertCallAvailable('ReadWorld')
    values = self.callFunction('ReadWorld', '{ "id": "%s" }' % id1)
    self.assertEqual(values["details"], "details")

    
  def test_exec_calls_characters(self):
    # Create a world for the characters
    result = self.callFunction('CreateWorld', '{ "name": "world 1" }')
    self.assertIsNotNone(result["id"])

    self.callFunction('ChangeState', '{ "state": "State_Edit_Characters" }')    

    # Read not existent character
    values = self.callFunction('ReadCharacter', '{ "id": "not_exist" }')
    self.assertIsNotNone(values.get("error"))
    
    # Create a character
    result = self.callFunction('CreateCharacter', '{ "name": "Bob" }')
    id = result["id"]
    self.assertIsNotNone(id)

    # Create a duplicate character
    result = self.callFunction('CreateCharacter', '{ "name": "Bob" }')
    self.assertIsNotNone(result.get("error"))

    # Read not existent character again
    values = self.callFunction('ReadCharacter', '{ "id": "not_exist" }')
    self.assertIsNotNone(values.get("error"))

    # Update a character
    result = self.callFunction('UpdateCharacter',
                               '{ "id": "' + id + '", "name": "Robert" }')
    self.assertIsNone(result.get("error"))
    
    
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

    result = self.callFunction('CreateCharacter','{ "name": "char 1" }')
    id = result["id"]

    # STATE EDIT CHARACTER
    self.assertEqual(self.chatFunctions.current_state,
                     chat_functions.STATE_EDIT_CHARACTERS)
    self.assertCallAvailable('UpdateCharacter')

    self.callFunction('UpdateCharacter',
                      '{ "id": "' + id + '", "name": "my char 1", ' +
                      ' "description": "a description", ' +
                      ' "details": "my details" }')

    values = self.callFunction('ReadCharacter',
                                '{ "id": "' + id + '" }')
    print(str(values))
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
    
