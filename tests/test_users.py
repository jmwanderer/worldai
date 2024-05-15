import os
import sqlite3
import unittest

from worldai import users

class BasicTestCase(unittest.TestCase):

    def setUp(self):
        self.dir_name = os.path.dirname(__file__)
        path = os.path.join(self.dir_name, "../worldai/schema.sql")
        self.db = sqlite3.connect("file::memory:")
        with open(path) as f:
            self.db.executescript(f.read())

    def tearDown(self) -> None:
        self.db.close()


    def testUserAdd(self):
        username = ""
        key = users.add_user(self.db, username)
        self.assertIsNotNone(key)

        key = users.add_user(self.db, username)
        self.assertIsNotNone(key)

        username = "Jim"
        key = users.add_user(self.db, username)
        self.assertIsNotNone(key)

    def testAuthGet(self):
        username = "Jim"
        key = users.add_user(self.db, username)
        self.assertIsNotNone(key)

        user_id = users.find_by_auth_key(self.db, "1")
        self.assertIsNone(user_id)

        user_id = users.find_by_auth_key(self.db, key)
        self.assertIsNotNone(user_id)

        is_admin = users.is_admin(self.db, user_id)
        self.assertFalse(is_admin)

        key_found = users.get_auth_key(self.db, "1")
        self.assertIsNone(key_found)

        key_found = users.get_auth_key(self.db, user_id)
        self.assertIsNotNone(key_found)



    def testAuthFind(self):
        username = "Jim"
        key1 = users.add_user(self.db, username)
        self.assertIsNotNone(key1)

        username = "Bob"
        key2 = users.add_user(self.db, username)
        self.assertIsNotNone(key2)
        self.assertNotEqual(key1, key2)

        username = "Joe"
        key3 = users.add_user(self.db, username)
        self.assertIsNotNone(key3)
        self.assertNotEqual(key1, key3)
        self.assertNotEqual(key2, key3)

        id1 = users.find_by_auth_key(self.db, key1)
        self.assertIsNotNone(id1)

        id2 = users.find_by_auth_key(self.db, key2)
        self.assertIsNotNone(id2)
        self.assertNotEqual(id1, id2)

        id3 = users.find_by_auth_key(self.db, key3)
        self.assertIsNotNone(id3)
        self.assertNotEqual(id1, id3)
        self.assertNotEqual(id2, id3)




