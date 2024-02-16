from worldai import elements
from worldai import chat_functions
from worldai import design_functions
from worldai import character_functions
from worldai import world_state

import unittest
import tempfile
import os
import sqlite3
import json


class DesignTestCase(unittest.TestCase):

    def setUp(self):
        self.dir_name = os.path.dirname(__file__)
        path = os.path.join(self.dir_name, "../worldai/schema.sql")
        self.db = sqlite3.connect(":memory:")
        with open(path) as f:
            self.db.executescript(f.read())
        self.user_dir = tempfile.TemporaryDirectory()
        self.chatFunctions = design_functions.DesignFunctions()

    def tearDown(self):
        self.db.close()
        self.user_dir.cleanup()

    def testProperties(self):
        props = self.chatFunctions.getProperties()
        value_1 = json.dumps(props)
        print(value_1)
        self.chatFunctions.setProperties(props)
        props = self.chatFunctions.getProperties()
        value_2 = json.dumps(props)
        assert value_1 == value_2

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
        self.db.execute(
            "INSERT INTO token_usage VALUES (?, 500, 500, 500, 5)", ("limits",)
        )
        self.db.commit()
        self.assertTrue(chat_functions.check_token_budgets(self.db))
        self.assertTrue(chat_functions.check_image_budget(self.db))

        chat_functions.track_tokens(self.db, 1, 300, 300, 300)
        chat_functions.count_image(self.db, 1, 3)

        self.assertFalse(chat_functions.check_token_budgets(self.db))
        self.assertFalse(chat_functions.check_image_budget(self.db))

    def test_exec_calls_world(self):
        self.assertCallAvailable("CreateWorld")
        result = self.callFunction("CreateWorld", '{ "name": "world 2" }')
        name2 = result["name"]
        self.assertIsNotNone(name2)

        # Check illegal state
        result = self.callFunction("ChangeState", '{ "state": "non existent" }')
        self.assertIsNotNone(result.get("error"))

        self.callFunction("ChangeState", '{ "state": "State_Worlds" }')

        self.assertCallAvailable("CreateWorld")
        result = self.callFunction("CreateWorld", '{ "name": "world 1" }')
        name1 = result["name"]
        self.assertIsNotNone(name1)

        self.callFunction("ChangeState", '{ "state": "State_Worlds" }')

        # Create duplicate name
        result = self.callFunction("CreateWorld", '{ "name": "world 1" }')
        self.assertIsNotNone(result.get("error"))

        self.assertCallAvailable("ListWorlds")
        values = self.callFunction("ListWorlds", "{}")
        self.assertEqual(len(values), 2)
        self.assertEqual(values[0]["name"], name2)
        self.assertEqual(values[1]["name"], name1)

        # Read not existent world
        values = self.callFunction("ShowWorld", '{ "name": "not_exist" }')
        self.assertIsNotNone(values.get("error"))

        self.assertCallAvailable("ShowWorld")
        values = self.callFunction("ShowWorld", '{ "name": "%s" }' % name1)
        self.assertEqual(len(values.get("details")), 0)

        self.callFunction("ChangeState", '{ "state": "State_World" }')

        self.assertCallAvailable("EditWorld")
        self.callFunction("EditWorld", "{}")

        self.assertCallAvailable("UpdateWorld")
        self.callFunction(
            "UpdateWorld",
            '{ "name": "world 1", '
            + ' "description": "a description", '
            + ' "details": "details" }',
        )

        self.assertCallAvailable("ShowWorld")
        values = self.callFunction("ShowWorld", '{ "name": "%s" }' % name1)
        self.assertEqual(values["details"], "details")

        # Test setting and getting plans
        values = self.callFunction("ReadPlans", '{ "name": "%s" }' % name1)
        self.assertEqual(values["plans"], "")
        self.callFunction("EditWorld", "{}")
        self.callFunction("UpdatePlans", '{ "plans": "my plans" }')
        values = self.callFunction("ReadPlans", '{ "name": "%s" }' % name1)
        self.assertEqual(values["plans"], "my plans")

        self.callFunction("ChangeState", '{ "state": "State_Documents" }')
        values = self.callFunction("ListDocuments", "{}")
        self.assertEqual(len(values), 0)

        self.callFunction("CreateDocument", '{ "name": "World History"}')

        values = self.callFunction("ListDocuments", "{}")
        self.assertEqual(len(values), 1)

        self.callFunction("CreateDocument", '{ "name": "People" }')
        values = self.callFunction("ListDocuments", "{}")
        self.assertEqual(len(values), 2)

        args = """{ "name": "World History",
              "heading": "Abstract",
               "content": "This is the abstract" }"""
        self.callFunction("AddDocumentSection", args)

        args = """{ "name": "World History",
              "heading": "Outline",
               "content": "This is the outline" }"""
        self.callFunction("AddDocumentSection", args)

        args = """{ "name": "World History",
              "heading": "Introduction",
              "content": "This is the intro" }"""
        self.callFunction("AddDocumentSection", args)

        args = """{ "name": "World History" }"""
        results = self.callFunction("ListDocumentSections", args)
        self.assertEqual(len(results), 3)

        args = """{ "name": "World History",
              "heading": "Introduction",
              "content": "This is a new" }"""
        self.callFunction("UpdateDocumentSection", args)

        args = """{ "name": "World History",
              "heading": "Introduction" }"""
        result = self.callFunction("ReadDocumentSection", args)
        self.assertEqual(result["content"], "This is a new")

    def test_exec_calls_characters(self):
        # Create a world for the characters
        result = self.callFunction("CreateWorld", '{ "name": "world 1" }')
        self.assertIsNotNone(result["name"])

        self.callFunction("ChangeState", '{ "state": "State_Characters" }')

        # Read not existent character
        values = self.callFunction("ShowCharacter", '{ "name": "not_exist" }')
        self.assertIsNotNone(values.get("error"))

        # Create a character
        result = self.callFunction("CreateCharacter", '{ "name": "Bob" }')
        name = result["name"]
        self.assertIsNotNone(name)

        # Create a duplicate character
        result = self.callFunction("CreateCharacter", '{ "name": "Bob" }')
        self.assertIsNotNone(result.get("error"))

        # Read not existent character again
        values = self.callFunction("ShowCharacter", '{ "name": "not_exist" }')
        self.assertIsNotNone(values.get("error"))

        # Update a character
        result = self.callFunction(
            "UpdateCharacter", '{ "name": "Bob", "new_name": "Robert" }'
        )
        self.assertIsNone(result.get("error"))

    def test_available_functions(self):
        # STATE_WORLDS
        functions = self.chatFunctions.get_available_tools()
        self.assertEqual(len(functions), 3)
        self.assertCallAvailable("ListWorlds")
        self.assertCallNotAvailable("UpdateWorld")
        self.assertIsNotNone(self.chatFunctions.get_state_instructions(self.db))
        self.assertIn("new world", self.chatFunctions.get_state_instructions(self.db))

        self.callFunction("CreateWorld", '{ "name": "world 1" }')

        # STATE WORLD
        self.assertEqual(self.chatFunctions.current_state, design_functions.STATE_WORLD)
        self.assertCallNotAvailable("UpdateWorld")
        self.assertCallNotAvailable("ListWorlds")
        self.assertIsNotNone(self.chatFunctions.get_state_instructions(self.db))
        self.assertIn("world", self.chatFunctions.get_state_instructions(self.db))
        self.callFunction("ChangeState", '{ "state": "State_World" }')

        # STATE WORLD
        self.assertEqual(self.chatFunctions.current_state, design_functions.STATE_WORLD)
        self.callFunction("ChangeState", '{ "state": "State_Characters" }')

        # STATE CHARACTERS
        self.assertEqual(
            self.chatFunctions.current_state, design_functions.STATE_CHARACTERS
        )
        self.assertCallNotAvailable("UpdateWorld")
        self.assertCallAvailable("ListCharacters")
        self.assertCallAvailable("CreateCharacter")
        self.assertCallAvailable("ShowCharacter")

        result = self.callFunction("CreateCharacter", '{ "name": "char 1" }')
        name = result["name"]

        # STATE CHARACTERS
        self.assertEqual(
            self.chatFunctions.current_state, design_functions.STATE_CHARACTERS
        )
        self.assertCallAvailable("UpdateCharacter")

        self.callFunction(
            "UpdateCharacter",
            '{ "name": "char 1", '
            + ' "new_name": "my char 1", '
            + ' "description": "a description", '
            + ' "details": "my details" }',
        )

        # Non-existant character
        result = self.callFunction(
            "UpdateCharacter",
            '{ "name": "char 1", '
            + ' "description": "a description", '
            + ' "details": "my details" }',
        )
        self.assertIsNotNone(result.get("error"))

        name = "my char 1"
        values = self.callFunction("ShowCharacter", '{ "name": "' + name + '" }')
        print(str(values))
        self.assertEqual(values["details"], "my details")
        self.assertEqual(values["name"], name)

        values = self.callFunction("ShowCharacter", '{ "name": "does not exist" }')
        self.assertIsNotNone(values.get("error"))

        values = self.callFunction("RemoveCharacter", '{ "name": "' + name + '" }')
        self.assertIsNone(values.get("error"))

        values = self.callFunction("RemoveCharacter", '{ "name": "does not exist" }')
        self.assertIsNotNone(values.get("error"))

        values = self.callFunction("RecoverCharacters", "{}")

        # STATE ITEMS
        self.callFunction("ChangeState", '{ "state": "State_Items" }')
        self.assertEqual(self.chatFunctions.current_state, design_functions.STATE_ITEMS)

        result = self.callFunction("CreateItem", '{ "name": "item 1" }')
        name = result["name"]

        self.callFunction(
            "UpdateItem",
            '{ "name": "item 1", '
            + ' "new_name": "my item 1", '
            + ' "description": "a description", '
            + ' "details": "my details" }',
        )

        # Not existant item
        result = self.callFunction(
            "UpdateItem",
            '{ "name": "item 1", '
            + ' "description": "a description", '
            + ' "details": "my details" }',
        )
        self.assertIsNotNone(result.get("error"))

        name = "my item 1"
        values = self.callFunction("ShowItem", '{ "name": "' + name + '" }')
        self.assertEqual(values["details"], "my details")
        self.assertEqual(values["name"], name)

        values = self.callFunction("ShowItem", '{ "name": "does not exist" }')
        self.assertIsNotNone(result.get("error"))

        values = self.callFunction("RemoveItem", '{ "name": "' + name + '" }')

        values = self.callFunction("RecoverItems", "{}")

        # Update item with ability
        result = self.callFunction(
            "UpdateItem",
            '{ "name": "my item 1", ' + ' "ability": { "effect": "sleep" }}',
        )
        self.assertIsNone(result.get("error"))
        values = self.callFunction("ShowItem", '{ "name": "' + name + '" }')
        self.assertEqual(values["ability"]["effect"], "sleep")

        # STATE SITES
        self.callFunction("ChangeState", '{ "state": "State_Sites" }')
        self.assertEqual(self.chatFunctions.current_state, design_functions.STATE_SITES)

        result = self.callFunction("CreateSite", '{ "name": "site 1" }')
        name = result["name"]

        self.callFunction(
            "UpdateSite",
            '{ "name": "site 1", '
            + ' "new_name": "my site 1", '
            + ' "description": "a description", '
            + ' "details": "my details" }',
        )

        # Non-existant site
        result = self.callFunction(
            "UpdateSite",
            '{ "name": "site 1", '
            + ' "description": "a description", '
            + ' "details": "my details" }',
        )
        self.assertIsNotNone(result.get("error"))

        name = "my site 1"
        values = self.callFunction("ShowSite", '{ "name": "' + name + '" }')
        self.assertEqual(values["details"], "my details")
        self.assertEqual(values["name"], name)

        values = self.callFunction("ShowSite", '{ "name": "does not exist" }')
        self.assertIsNotNone(result.get("error"))

        values = self.callFunction("RemoveSite", '{ "name": "' + name + '" }')

        values = self.callFunction("RecoverSites", "{}")

        # Update item with open site ability
        self.callFunction("ChangeState", '{ "state": "State_Items" }')
        result = self.callFunction(
            "UpdateItem",
            '{ "name": "my item 1", '
            + ' "ability": '
            + '{ "effect": "open", "site": "my site 1" }}',
        )
        self.assertIsNone(result.get("error"))
        values = self.callFunction("ShowItem", '{ "name": "my item 1" }')
        self.assertEqual(values["ability"]["site"], "my site 1")

        # Use a non-existant site
        result = self.callFunction(
            "UpdateItem",
            '{ "name": "my item 1", '
            + ' "ability": '
            + '{ "effect": "open", "site": "no site" }}',
        )
        self.assertIsNotNone(result.get("error"))

        # Create an item with ability
        result = self.callFunction(
            "CreateItem",
            '{ "name": "item 99",'
            + '"mobile": "false",'
            + '"ability": { "effect": "open",'
            + '"site": "my site 1" }}',
        )
        self.assertIsNone(result.get("error"))
        values = self.callFunction("ShowItem", '{ "name": "item 99" }')
        self.assertEqual(values["ability"]["site"], "my site 1")
        self.assertEqual(values["ability"]["effect"], "open")

        # Create with non-existant site
        result = self.callFunction(
            "CreateItem",
            '{ "name": "item 99",'
            + '"mobile": "false",'
            + '"ability": { "effect": "open",'
            + '"site": "no site" }}',
        )
        self.assertIsNotNone(result.get("error"))

        self.callFunction("ChangeState", '{ "state": "State_World" }')
        self.assertEqual(self.chatFunctions.current_state, design_functions.STATE_WORLD)

    def assertCallAvailable(self, name):
        # Assert we are allowed to call the function in the current state
        functions = self.chatFunctions.get_available_tools()
        names = [x["function"]["name"] for x in functions]
        self.assertIn(name, names)

    def assertCallNotAvailable(self, name):
        # Assert we are allowed to call the function in the current state
        functions = self.chatFunctions.get_available_tools()
        names = [x["function"]["name"] for x in functions]
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


class CharacterTestCase(unittest.TestCase):

    def setUp(self):
        self.dir_name = os.path.dirname(__file__)
        path = os.path.join(self.dir_name, "../worldai/schema.sql")
        self.db = sqlite3.connect(":memory:")
        with open(path) as f:
            self.db.executescript(f.read())
        self.user_dir = tempfile.TemporaryDirectory()

        # Load test data
        path = os.path.join(os.path.dirname(__file__), "test_data.sql")
        with open(path) as f:
            self.db.executescript(f.read())

        worlds = elements.listWorlds(self.db)
        world_id = worlds[0].id

        characters = elements.listCharacters(self.db, world_id)
        character_id = characters[0].id

        session_id = "1234"
        wstate_id = world_state.getWorldStateID(self.db, session_id, world_id)

        self.chatFunctions = character_functions.CharacterFunctions(
            wstate_id, world_id, character_id
        )

    def tearDown(self):
        self.db.close()
        self.user_dir.cleanup()

    def testProperties(self):
        props = self.chatFunctions.getProperties()
        value_1 = json.dumps(props)
        print(value_1)
        self.chatFunctions.setProperties(props)
        props = self.chatFunctions.getProperties()
        value_2 = json.dumps(props)
        assert value_1 == value_2


if __name__ == "__main__":
    unittest.main()
