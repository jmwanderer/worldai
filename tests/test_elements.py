from worldai import elements
import worldai
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

    f = elements.getImageFile(self.db, self.user_dir.name, image.id)
    data = f.read()
    f.close()
      
  def testCase(self):
    world = elements.World("world 1", "description", "details", '{ "dog": "kona" }')
    world = elements.createWorld(self.db, world)
    world = elements.World("world 2", "description", "details", '{ "dog": "kona" }')
    world = elements.createWorld(self.db, world)

    character = elements.Character(world.id, "char 1", "desc", "details")
    character = elements.createCharacter(self.db, character)
    character = elements.Character(world.id, "char 2", "desc", "details")
    character = elements.createCharacter(self.db, character)

    site = elements.Site(world.id, "site 1", "desc", "details")
    site = elements.createSite(self.db, site)
    site = elements.Site(world.id, "site 2", "desc", "details")
    site = elements.createSite(self.db, site)

    item = elements.Item(world.id, "item 1", "desc", "details")
    item = elements.createItem(self.db, item)
    item = elements.Item(world.id, "item 2", "desc", "details")
    item = elements.createItem(self.db, item)
  
    print("list worlds")
    worlds = elements.listWorlds(self.db)
    print(str(worlds))

    print("load world")
    world = elements.loadWorld(self.db, world.id)
    print(str(world))

    print("list characters")
    characters = elements.listCharacters(self.db, world.id)
    print(str(characters))

    print("load character")
    character = elements.loadCharacter(self.db, characters[0]["id"])
    print(str(character))

    print("\nlist sites")
    sites = elements.listSites(self.db, world.id)
    print(str(sites))

    print("\nload site")
    site = elements.loadSite(self.db, sites[0]["id"])
    print(str(site))

    print("\nlist items")
    items = elements.listItems(self.db, world.id)
    print(str(items))

    print("\nload item")
    item = elements.loadItem(self.db, items[0]["id"])
    print(str(item))
  
    print("\nupdate item")
    item.description = "a new description"
    elements.updateItem(self.db, item)
    item = elements.loadItem(self.db, items[0]["id"])
    print(str(item))  


if __name__ ==  '__main__':
  unittest.main()
