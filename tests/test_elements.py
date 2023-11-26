from worldai import elements
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

  def testImages(self):
    f = open(os.path.join(self.dir_name, "trees.png"), "rb")
    image = elements.createImage(self.db, self.user_dir.name, f)
    f.close()
    self.assertIsNotNone(image)

    f = elements.getImageFile(self.db, self.user_dir.name, image.id)
    data = f.read()
    f.close()
    self.assertEqual(len(data), 2366609)
      
  def testCRU(self):
    # Create world
    world = elements.World("world 1", "description", "details",
                           '{ "dog": "kona" }')
    world1 = elements.createWorld(self.db, world)
    self.assertIsNotNone(world)

    # Create world
    world = elements.World("world 2", "description", "details",
                           '{ "dog": "kona" }')
    world2 = elements.createWorld(self.db, world)
    self.assertIsNotNone(world)    

    # Create character
    character = elements.Character(world1.id, "char 1", "desc", "details")
    character = elements.createCharacter(self.db, character)
    self.assertIsNotNone(character)

    # Create character    
    character = elements.Character(world1.id, "char 2", "desc", "details")
    character = elements.createCharacter(self.db, character)
    self.assertIsNotNone(character)

    # Create character    
    character = elements.Character(world1.id, "char 3", "desc", "details")
    character = elements.createCharacter(self.db, character)
    self.assertIsNotNone(character)

    # Create character - diff world
    character = elements.Character(world2.id, "char1", "world 2 char",
                                   "details")
    character = elements.createCharacter(self.db, character)
    self.assertIsNotNone(character)

    # Create site    
    site = elements.Site(world1.id, "site 1", "desc", "details")
    site = elements.createSite(self.db, site)
    self.assertIsNotNone(site)

    # Create site        
    site = elements.Site(world1.id, "site 2", "desc", "details")
    site = elements.createSite(self.db, site)
    self.assertIsNotNone(site)

    # Create item
    item = elements.Item(world1.id, "item 1", "desc", "details")
    item = elements.createItem(self.db, item)
    self.assertIsNotNone(item)

    # Create item
    item = elements.Item(world1.id, "item 2", "desc", "details")
    item = elements.createItem(self.db, item)
    self.assertIsNotNone(item)

    # List worlds
    worlds = elements.listWorlds(self.db)
    self.assertEqual(len(worlds), 2)

    # Read world
    world = elements.loadWorld(self.db, world1.id)
    self.assertIsNotNone(world)
    self.assertEqual(world.name, "world 1")
    self.assertEqual(world.description, "description")
    self.assertEqual(world.details, "details")    
    self.assertEqual(world.dog, "kona")

    # Update world
    world.name="world 3"
    world.description="another description"
    elements.updateWorld(self.db, world)
    world = elements.loadWorld(self.db, world1.id)
    self.assertIsNotNone(world)
    self.assertEqual(world.name, "world 3")
    self.assertEqual(world.description, "another description")
    self.assertEqual(world.details, "details")    
    self.assertEqual(world.dog, "kona")

    # List characters
    characters = elements.listCharacters(self.db, world1.id)
    self.assertEqual(len(characters), 3)

    # Load character
    character = elements.loadCharacter(self.db, characters[0]["id"])
    self.assertIsNotNone(character)

    # List sites
    sites = elements.listSites(self.db, world1.id)
    self.assertEqual(len(sites), 2)
    
    # Load site
    site = elements.loadSite(self.db, sites[0]["id"])
    self.assertIsNotNone(site)

    # List items
    items = elements.listItems(self.db, world1.id)
    self.assertEqual(len(items), 2)    

    # Load item
    item = elements.loadItem(self.db, items[0]["id"])
    self.assertIsNotNone(item)

    # Update item
    item.description = "a new description"
    elements.updateItem(self.db, item)
    item = elements.loadItem(self.db, items[0]["id"])
    self.assertIsNotNone(item)
    self.assertEqual(item.description, "a new description")


if __name__ ==  '__main__':
  unittest.main()
