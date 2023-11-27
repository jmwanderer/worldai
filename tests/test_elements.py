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
    world = elements.World()
    world.setPropertiesJSON('{ "' + elements.PROP_NAME + '": "world 1", ' +
                            '"' + elements.PROP_DESCRIPTION +
                            '": "description" }')
    world.setDetails("details")
    world1 = elements.createWorld(self.db, world)
    self.assertIsNotNone(world)

    # Create world
    world = elements.World()
    world.setProperties({ elements.PROP_NAME: "world 2",
                          elements.PROP_DESCRIPTION: "description"})
    world2 = elements.createWorld(self.db, world)
    self.assertIsNotNone(world)    

    # Create character
    character = elements.Character(world1.id)
    character.setProperties({ elements.PROP_NAME: "char1",
                              elements.PROP_DESCRIPTION: "description",
                              elements.PROP_DETAILS: "details"})
    
    character.updateProperties({ elements.PROP_DETAILS: "my details"})
    character = elements.createCharacter(self.db, character)
    self.assertIsNotNone(character)

    # Create character    
    character = elements.Character(world1.id)
    character.setName("char 2")
    character.setDescription("description")
    character.setDetails("details")
    character = elements.createCharacter(self.db, character)
    self.assertIsNotNone(character)

    # Create character    
    character = elements.Character(world1.id)
    character.setName("char 3")

    character = elements.createCharacter(self.db, character)
    self.assertIsNotNone(character)

    # Create character - diff world
    character = elements.Character(world2.id)
    character.setName("char 1")
    character.setDescription("world 2 char")
    character = elements.createCharacter(self.db, character)
    self.assertIsNotNone(character)

    # Create site    
    site = elements.Site(world1.id)
    site.setName("site 1")
    site = elements.createSite(self.db, site)
    self.assertIsNotNone(site)

    # Create site        
    site = elements.Site(world1.id)
    site.setName("site 2")
    site = elements.createSite(self.db, site)
    self.assertIsNotNone(site)

    # Create item
    item = elements.Item(world1.id)
    item.setName("item 1")
    item = elements.createItem(self.db, item)
    self.assertIsNotNone(item)

    # Create item
    item = elements.Item(world1.id)
    item.setName("item 2")    
    item = elements.createItem(self.db, item)
    self.assertIsNotNone(item)

    # List worlds
    worlds = elements.listWorlds(self.db)
    self.assertEqual(len(worlds), 2)

    # Read world
    world = elements.loadWorld(self.db, world1.id)
    self.assertIsNotNone(world)
    self.assertEqual(world.getName(), "world 1")
    self.assertEqual(world.getDescription(), "description")
    self.assertEqual(world.getDetails(), "details")    

    # Update world
    world.setName("world 3")
    world.setDescription("another description")
    elements.updateWorld(self.db, world)
    world = elements.loadWorld(self.db, world1.id)
    self.assertIsNotNone(world)
    self.assertEqual(world.getName(), "world 3")
    self.assertEqual(world.getDescription(), "another description")
    self.assertEqual(world.getDetails(), "details")    

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
    item.setDescription("a new description")
    elements.updateItem(self.db, item)
    item = elements.loadItem(self.db, items[0]["id"])
    self.assertIsNotNone(item)
    self.assertEqual(item.getDescription(), "a new description")


if __name__ ==  '__main__':
  unittest.main()
