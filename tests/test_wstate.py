# Unit test for world state

import random
import unittest

from worldai import world_state, elements


class BasicTestCase(unittest.TestCase):

    def setUp(self):
        self.wstate = world_state.WorldState("id0000")
        self.char_ids = ["idc1", "idc2", "idc3"]
        self.item_ids = ["idi1", "idi2", "idi3"]
        self.site_ids = ["ids1", "ids2", "ids3"]

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
            if self.wstate.model.item_state.get(iid) is None:
                pid = random.choice(places)
                self.wstate.setItemLocation(iid, pid)

    def testStateString(self):
        self.assertIsNotNone(self.wstate.get_model_str())
        wstate = world_state.WorldState("id0001")
        wstate.set_model_str(self.wstate.get_model_str())
        for cid in self.char_ids:
            self.assertTrue(wstate.getCharacterLocation(cid) in self.site_ids)

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
        self.wstate.setCharacterHealth(cid, 1000)
        self.assertEqual(self.wstate.getCharacterHealth(cid), 1000)

        # Credits
        self.assertEqual(self.wstate.getCharacterCredits(cid), 1000)
        self.wstate.setCharacterCredits(cid, 2000)
        self.assertEqual(self.wstate.getCharacterCredits(cid), 2000)

        # Status
        sleeping = elements.CharStatus.SLEEPING
        poisoned = elements.CharStatus.POISONED
        self.assertFalse(self.wstate.hasPlayerStatus(sleeping))
        self.wstate.addPlayerStatus(sleeping)
        self.wstate.addPlayerStatus(poisoned)
        self.assertTrue(self.wstate.hasPlayerStatus(sleeping))
        self.assertTrue(self.wstate.hasPlayerStatus(poisoned))
        self.wstate.removePlayerStatus(poisoned)
        self.assertTrue(self.wstate.hasPlayerStatus(sleeping))
        self.assertFalse(self.wstate.hasPlayerStatus(poisoned))

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

    def testSiteFunctions(self):
        site_id = self.site_ids[0]
        self.assertTrue(self.wstate.isSiteOpen(site_id))
        self.wstate.setSiteOpen(site_id, False)
        self.assertFalse(self.wstate.isSiteOpen(site_id))

    def testPlayerFunctions(self):
        cid = self.char_ids[0]
        iid = self.item_ids[0]
        sid = self.site_ids[0]

        self.assertFalse(self.wstate.hasItem(iid))
        self.wstate.addItem(iid)
        self.assertTrue(self.wstate.hasItem(iid))
        self.wstate.selectItem(iid)
        self.assertNotEqual(len(self.wstate.getSelectedItem()), 0)
        self.wstate.dropItem(iid)
        self.assertFalse(self.wstate.hasItem(iid))
        self.assertEqual(len(self.wstate.getSelectedItem()), 0)

        self.wstate.addItem(iid)
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
        self.assertEqual(self.wstate.getPlayerCredits(), 1000)
        self.wstate.setPlayerCredits(2000)
        self.assertEqual(self.wstate.getPlayerCredits(), 2000)

    def testEvents(self):
        cid1 = self.char_ids[0]
        cid2 = self.char_ids[1]
        event1 = "event #1"
        event2 = "event #2"
        event3 = "event #3"

        self.assertIsNone(self.wstate.removeCharacterEvent(cid1))
        self.wstate.addCharacterEvent(cid1, event1)
        self.assertIsNotNone(self.wstate.removeCharacterEvent(cid1))
        self.assertIsNone(self.wstate.removeCharacterEvent(cid1))
        self.wstate.addCharacterEvent(cid2, event1)
        self.assertIsNone(self.wstate.removeCharacterEvent(cid1))
        self.assertIsNotNone(self.wstate.removeCharacterEvent(cid2))
        self.assertIsNone(self.wstate.removeCharacterEvent(cid2))

        self.wstate.addCharacterEvent(cid1, event1)
        self.wstate.addCharacterEvent(cid1, event2)
        self.wstate.addCharacterEvent(cid2, event1)
        self.wstate.addCharacterEvent(cid1, event3)
        self.wstate.addCharacterEvent(cid2, event2)
        self.wstate.addCharacterEvent(cid2, event3)

        event = self.wstate.removeCharacterEvent(cid1)
        self.assertEqual(event, event1)
        event = self.wstate.removeCharacterEvent(cid1)
        self.assertEqual(event, event2)
        event = self.wstate.removeCharacterEvent(cid1)
        self.assertEqual(event, event3)
        event = self.wstate.removeCharacterEvent(cid1)
        self.assertIsNone(event)

        events = self.wstate.getCharacterEvents(cid2)
        self.assertEqual(len(events), 3)
        events = self.wstate.getCharacterEvents(cid2)
        self.assertEqual(len(events), 0)

    def testEndConditionEval(self):
        cid1 = self.char_ids[0]
        sid1 = self.site_ids[0]
        sid2 = self.site_ids[1]
        iid1 = self.item_ids[0]
        iid2 = self.item_ids[1]

        world = elements.World()

        prop = elements.Condition.characterAt(cid1, sid1)
        world.endConditions().append(prop)
        self.wstate.setCharacterLocation(cid1, sid2)
        self.assertFalse(world_state.evalEndCondition(self.wstate, prop))
        self.wstate.setCharacterLocation(cid1, sid1)
        self.assertTrue(world_state.evalEndCondition(self.wstate, prop))

        prop = elements.Condition.characterHas(cid1, iid1)
        world.endConditions().append(prop)
        self.wstate.setItemLocation(iid1, sid1)
        self.assertFalse(world_state.evalEndCondition(self.wstate, prop))
        self.wstate.setItemLocation(iid1, cid1)
        self.assertTrue(world_state.evalEndCondition(self.wstate, prop))

        prop = elements.Condition.itemAt(iid2, sid2)
        world.endConditions().append(prop)
        self.wstate.setItemLocation(iid2, sid1)
        self.assertFalse(world_state.evalEndCondition(self.wstate, prop))
        self.wstate.setItemLocation(iid2, sid2)
        self.assertTrue(world_state.evalEndCondition(self.wstate, prop))

        prop = elements.Condition.characterIs(cid1, elements.CharStatus.SLEEPING)
        world.endConditions().append(prop)
        self.assertFalse(world_state.evalEndCondition(self.wstate, prop))
        self.wstate.addCharacterStatus(cid1, elements.CharStatus.SLEEPING)
        self.assertTrue(world_state.evalEndCondition(self.wstate, prop))

        self.assertTrue(world_state.evalEndConditions(self.wstate, world))
        self.assertTrue(self.wstate.checkEndConditions(world))

        self.wstate.setItemLocation(iid2, sid1)
        self.assertFalse(world_state.evalEndConditions(self.wstate, world))
        # A win is sticky, verify
        self.assertTrue(self.wstate.checkEndConditions(world))

        # TODO: test ConditionVerb.USES


 




