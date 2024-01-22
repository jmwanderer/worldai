# Unit test for world state

from worldai import world_state
import unittest
import random

class BasicTestCase(unittest.TestCase):

  def setUp(self):
    self.wstate = world_state.WorldState("id0000")
    self.char_ids = [ "idc1", "idc2", "idc3" ]
    self.item_ids = [ "idi1", "idi2", "idi3" ]
    self.site_ids = [ "ids1", "ids2", "ids3" ]

    # Assign characters to sites
    for cid in self.char_ids:
      if self.wstate.getCharacterLocation(cid) == "":
        sid = random.choice(self.site_ids)
        self.wstate.setCharacterLocation(cid, sid)

    # Set item locations (character or site)
    places = []
    places.extend(self.char_ids)
    places.extend(self.site_ids)

    for iid in self.item_ids:
      if self.wstate.item_state.get(iid) is None:
        pid = random.choice(places)
        self.wstate.setItemLocation(iid, pid)
    
  def testStateStrings(self):
    self.assertIsNotNone(self.wstate.get_player_state_str())
    self.assertIsNotNone(self.wstate.get_character_state_str())
    self.assertIsNotNone(self.wstate.get_item_state_str())

  def testCharFunctions(self):
    # Functions for character state
    
    # character locations
    count = 0
    for sid in self.site_ids:
      count += len(self.wstate.getCharactersAtLocation(sid))
    self.assertEqual(count, len(self.char_ids))

    cid = self.char_ids[0]
    # Strength
    self.assertEqual(self.wstate.getCharacterStrength(cid), 8)
    self.wstate.setCharacterStrength(cid, 1000)
    self.assertEqual(self.wstate.getCharacterStrength(cid), 1000)

    # Health
    self.assertEqual(self.wstate.getCharacterHealth(cid), 10)
    self.wstate.setCharacterHealth(cid, 100)
    self.assertEqual(self.wstate.getCharacterHealth(cid), 100)
    
    # Credits
    self.assertEqual(self.wstate.getCharacterCredits(cid), 100)
    self.wstate.setCharacterCredits(cid, 2000)
    self.assertEqual(self.wstate.getCharacterCredits(cid), 2000)


  def testItemFunctions(self):
    # character items
    count = 0
    for cid in self.char_ids:
      count += len(self.wstate.getCharacterItems(cid))
      
    for sid in self.site_ids:
      count += len(self.wstate.getItemsAtLocation(sid))

    self.assertEqual(count, len(self.item_ids))

    cid = self.char_ids[0]
    iid = self.item_ids[0]    

    self.wstate.addCharacterItem(cid, iid)
    self.assertTrue(self.wstate.hasCharacterItem(cid, iid))

    
  def testPlayerFunctions(self):
    cid = self.char_ids[0]
    iid = self.item_ids[0]
    sid = self.site_ids[0]    

    self.assertFalse(self.wstate.hasItem(iid))    
    self.wstate.addItem(iid)
    self.assertTrue(self.wstate.hasItem(iid))
    
    self.assertEqual(len(self.wstate.getItems()), 1)

    self.assertEqual(self.wstate.getFriendship(cid), 0)
    self.wstate.increaseFriendship(cid)
    self.assertTrue(self.wstate.getFriendship(cid) > 0)   
    self.wstate.decreaseFriendship(cid)
    self.assertEqual(self.wstate.getFriendship(cid), 0)    

    self.wstate.setChatCharacter(cid)
    self.assertEqual(self.wstate.getChatCharacter(), cid)
    self.wstate.setChatCharacter(None)
    self.assertNotEqual(self.wstate.getChatCharacter(), cid)

    self.assertEqual(self.wstate.getLocation(), "")
    self.wstate.setLocation(sid)
    self.assertEqual(self.wstate.getLocation(), sid)

    # Strength
    self.assertEqual(self.wstate.getPlayerStrength(), 8)
    self.wstate.setPlayerStrength(1000)
    self.assertEqual(self.wstate.getPlayerStrength(), 1000)

    # Health
    self.assertEqual(self.wstate.getPlayerHealth(), 10)
    self.wstate.setPlayerHealth(100)
    self.assertEqual(self.wstate.getPlayerHealth(), 100)
    
    # Credits
    self.assertEqual(self.wstate.getPlayerCredits(), 100)
    self.wstate.setPlayerCredits(2000)
    self.assertEqual(self.wstate.getPlayerCredits(), 2000)

    