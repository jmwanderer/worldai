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

  def createImageFile(self, filename):
    f_in = open(os.path.join(self.dir_name, "trees.png"), "rb")
    f_out = open(os.path.join(self.user_dir.name, filename), "wb")
    f_out.write(f_in.read())
    f_in.close()
    f_out.close()
    
  def testImages(self):
    parent_id = "my_parent"

    images = elements.getImages(self.db, parent_id)
    self.assertEqual(len(images), 0)
    
    image = elements.Image()
    image.setPrompt("a prompt")
    image.setParentId(parent_id)
    self.createImageFile(image.getFilename())
    image = elements.createImage(self.db, image)
    self.assertIsNotNone(image)

    images = elements.getImages(self.db, parent_id)
    self.assertEqual(len(images), 1)
    

    f = elements.getImageFile(self.db, self.user_dir.name, image.id)
    data = f.read()
    f.close()
    self.assertEqual(len(data), 2366609)

    elements.hideImage(self.db, image.id)
    images = elements.getImages(self.db, parent_id)
    self.assertEqual(len(images), 0)

    count = elements.recoverImages(self.db, parent_id)
    self.assertEqual(count, 1)
    images = elements.getImages(self.db, parent_id)
    self.assertEqual(len(images), 1)

    elements.deleteImage(self.db, self.user_dir.name, image.id)
    

  def testBasic(self):
    self.assertEqual(elements.ElementType.WorldType(), "World")
    self.assertEqual(elements.ElementType.CharacterType(), "Character")
    self.assertEqual(elements.ElementType.ItemType(), "Item")
    self.assertEqual(elements.ElementType.SiteType(), "Site")    
      
  def testCRU(self):
    # Create world
    world = elements.World()
    world.setPropertiesJSON('{ "' + elements.PROP_NAME + '": "world 1", ' +
                            '"' + elements.PROP_DESCRIPTION +
                            '": "description" }')
    world.setDetails("details")
    world1 = elements.createWorld(self.db, world)
    self.assertIsNotNone(world)

    tag = elements.getElemTag(self.db, world.id)
    self.assertEqual(tag.getID(), world.id)
    self.assertEqual(tag.getWorldID(), world.id)
    self.assertEqual(tag.getType(), elements.ElementType.WorldType())

    # Create world
    world = elements.World()
    world.setName("w2")
    world2 = elements.createWorld(self.db, world)
    world2.setProperties({ elements.PROP_NAME: "world 2",
                           elements.PROP_DESCRIPTION: "description"})
    world2.setPlans("Characters:\n-Paige\n-Grant\n-Malia\n-Jake")
    elements.updateWorld(self.db, world)
    world2 = elements.loadWorld(self.db, world2.id)
    self.assertEqual(world2.getName(), "world 2")
    self.assertIsNotNone(world)
    self.assertIsNotNone(world2.getPlans())

    characters = elements.listCharacters(self.db, world1.id)
    self.assertEqual(len(characters), 0)
    
    # Create character
    character = elements.Character(world1.id)
    character.setProperties({ elements.PROP_NAME: "char1",
                              elements.PROP_DESCRIPTION: "description",
                              elements.PROP_DETAILS: "details"})
    
    character.updateProperties({ elements.PROP_DETAILS: "my details"})
    character = elements.createCharacter(self.db, character)
    self.assertIsNotNone(character)

    characters = elements.listCharacters(self.db, world1.id)
    self.assertEqual(len(characters), 1)
    
    elements.hideCharacter(self.db, character.id)
    characters = elements.listCharacters(self.db, world1.id)
    self.assertEqual(len(characters), 0)
    
    count = elements.recoverCharacters(self.db, world1.id)
    self.assertEqual(count, 1)    
    characters = elements.listCharacters(self.db, world1.id)
    self.assertEqual(len(characters), 1)

    tag = elements.getElemTag(self.db, character.id)
    self.assertEqual(tag.getID(), character.id)
    self.assertEqual(tag.getWorldID(), world1.id)
    self.assertEqual(tag.getType(), elements.ElementType.CharacterType())
    

    # Create character    
    character = elements.Character(world1.id)
    character.setName("char 2")
    character.setDescription("description")
    character.setDetails("details")
    character.setPersonality("personality")    
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

    sites = elements.listSites(self.db, world1.id)
    self.assertEqual(len(sites), 0)

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

    self.assertFalse(site.getDefaultLocked())
    site.setDefaultLocked(True)
    elements.updateSite(self.db, site)
    site = elements.loadSite(self.db, site.id)
    self.assertTrue(site.getDefaultLocked())

    sites = elements.listSites(self.db, world1.id)
    self.assertEqual(len(sites), 2)

    elements.hideSite(self.db, site.id)
    sites = elements.listSites(self.db, world1.id)
    self.assertEqual(len(sites), 1)

    count = elements.recoverSites(self.db, world1.id)
    self.assertEqual(count, 1)
    sites = elements.listSites(self.db, world1.id)
    self.assertEqual(len(sites), 2)
    

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

    items = elements.listItems(self.db, world1.id)
    self.assertEqual(len(items), 2)

    elements.hideItem(self.db, item.id)
    items = elements.listItems(self.db, world1.id)
    self.assertEqual(len(items), 1)

    count = elements.recoverItems(self.db, world1.id)
    self.assertEqual(count, 1)
    items = elements.listItems(self.db, world1.id)
    self.assertEqual(len(items), 2)

    self.assertTrue(item.getIsMobile())
    itemAbility = elements.ItemAbility(elements.ItemAction.APPLY,
                                       elements.CharState.CAPTURED)
    item.setAbility(itemAbility)
    item.setIsMobile(False)
    elements.updateItem(self.db, item)
    item = elements.loadItem(self.db, item.id)
    self.assertEqual(item.getAbility().getAction(),
                     elements.ItemAction.APPLY)                     
    self.assertFalse(item.getIsMobile())

    # List worlds
    worlds = elements.listWorlds(self.db)
    self.assertEqual(len(worlds), 2)
    (prev_world, next_world) = elements.getAdjacentElements(worlds[0], worlds)
    self.assertIsNone(prev_world)
    self.assertIsNotNone(next_world)

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

    # Create character image
    char_id = characters[0].getID()
    image = elements.Image()
    image.setPrompt("a prompt")
    image.setParentId(char_id)
    self.createImageFile(image.getFilename())
    image = elements.createImage(self.db, image)
    print("char id %s, image parent %s" % (char_id, image.parent_id))
    self.assertIsNotNone(image)

    # Load character
    character = elements.loadCharacter(self.db, char_id)
    self.assertIsNotNone(character)
    self.assertEqual(len(character.getImages()), 1)

    # List sites
    sites = elements.listSites(self.db, world1.id)
    self.assertEqual(len(sites), 2)
    
    # Load site
    site = elements.loadSite(self.db, sites[0].getID())
    self.assertIsNotNone(site)

    # List items
    items = elements.listItems(self.db, world1.id)
    self.assertEqual(len(items), 2)    

    # Load item
    item = elements.loadItem(self.db, items[0].getID())
    self.assertIsNotNone(item)

    # Update item
    item.setDescription("a new description")
    elements.updateItem(self.db, item)
    item = elements.loadItem(self.db, items[0].getID())
    self.assertIsNotNone(item)
    self.assertEqual(item.getDescription(), "a new description")


if __name__ ==  '__main__':
  unittest.main()
