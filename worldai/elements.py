#!/usr/bin/env python3
"""
Represets the element of a world definition.
"""

import datetime
import os
import json
import sqlite3

class ElementType:
  """
  Types of elements in a world.
  """
  NONE = 0
  WORLD = 1
  CHARACTER = 2
  SITE = 3
  ITEM = 4

  typeNames = [ "None",
                "World",
                "Character",                
                "Site",
                "Item" ]

  def typeToName(element_type):
    return ElementType.typeNames[element_type]


class Element:
  """
  Represents an element building block of a world
  """
  def __init__(self, element_type, parent_id, name,
               description, details, properties):
    self.id = 0
    self.type = element_type
    self.setCoreValues((parent_id, name, description, details, properties))

  def setCoreValues(self, values):
    self.parent_id = values[0]    
    self.name = values[1]
    self.description = values[2]
    self.details = values[3]
    self.setProperties(json.loads(values[4]))

  def setProperties(self, properties):
    pass

  def getProperties(self):
    return {}

  def __str__(self):
    type_str = ElementType.typeToName(self.type)
    propStr = json.dumps(self.getProperties())
    return (f"type: {self.type}, id: {self.id}, parent_id: {self.parent_id}, "
            + f"name: {self.name}, description: {self.description}, "
            + f"details: {self.details}, properties: {propStr}")
                       
class World(Element):
  """
  Represents an instance of a World.
  """
  def __init__(self, name="", description="", details="", properties="{}"):
    super().__init__(ElementType.WORLD, 0, name, description,
                     details, properties)

  def setProperties(self, properties):
    self.dog = properties.get("dog", "")

  def getProperties(self):
    return { "dog": self.dog }
  
class Character(Element):
  """
  Represents an instance of a Character.
  """
  def __init__(self, parent_id=0, name="", description="",
               details="", properties="{}"):
    super().__init__(ElementType.CHARACTER, parent_id, name, description,
                     details, properties)
    
class Site(Element):
  """
  Represents an instance of a Character.
  """
  def __init__(self, parent_id=0, name="", description="",
               details="", properties="{}"):
    super().__init__(ElementType.SITE, parent_id, name, description,
                     details, properties)

class Item(Element):
  """
  Represents an instance of a Character.
  """
  def __init__(self, parent_id=0, name="", description="",
               details="", properties="{}"):
    super().__init__(ElementType.ITEM, parent_id, name, description,
                     details, properties)
    

                       
class ElementStore:
  def loadElement(db, id, element):
    """
    Return an element insance
    """
    q = db.execute("SELECT parent_id, name, description, details, properties " +
                   "FROM elements WHERE id = ? and type = ?",
                   (id, element.type))
    r = q.fetchone()
    if r is not None:
      element.id = id
      element.setCoreValues(r)
      return element
    return None

  def updateElement(db, element):
    q = db.execute("UPDATE elements SET  name = ?, description = ?, " +
                   "details = ?, properties = ? " +
                   "WHERE id = ? and type = ?",
                   (element.name, element.description, element.details,
                    json.dumps(element.getProperties()), element.id,
                               element.type))
    db.commit()    
 
  def createElement(db, element):
    """
    Return an element insance
    """
    q = db.execute("INSERT INTO elements VALUES (null, ?, ?, ?, ?, ?, ?)",
                   (element.parent_id, element.name, element.type,
                    element.description, element.details,
                    json.dumps(element.getProperties())))
    q = db.execute("SELECT last_insert_rowid()")
    id = q.fetchone()[0]
    db.commit()
    element.id = id
    return element
  
  def getElements(db, element_type, parent_id):
    """
    Return a list of elements: id and name
    """
    result = []
    q = db.execute("SELECT id, name FROM elements WHERE " +
                   "type = ? AND parent_id = ?", (element_type, parent_id))
    for (id, name) in q.fetchall():
      result.append({ "id": id, "name" :  name })

    return result
  

class Elements:  
  def listWorlds(db):
    """
    Return a list of worlds.
    """
    return ElementStore.getElements(db, ElementType.WORLD, 0)

  def loadWorld(db, id):
    """
    Return a world instance
    """
    return ElementStore.loadElement(db, id, World())

  def createWorld(db, world):
    """
    Return a world instance
    """
    return ElementStore.createElement(db, world)

  def updateWorld(db, world):
    ElementStore.updateElement(db, world)
  
  def listCharacters(db, world_id):
    """
    Return a list of characters.
    """
    return ElementStore.getElements(db, ElementType.CHARACTER, world_id)

  def loadCharacter(db, id):
    """
    Return a character instance
    """
    return ElementStore.loadElement(db, id, Character())

  def createCharacter(db, character):
    """
    Return a character instance
    """
    return ElementStore.createElement(db, character)

  def updateCharacter(db, character):
    ElementStore.updateElement(db, character)

  def listSites(db, world_id):
    """
    Return a list of sites.
    """
    return ElementStore.getElements(db, ElementType.SITE, world_id)

  def loadSite(db, id):
    """
    Return a site instance
    """
    return ElementStore.loadElement(db, id, Site())

  def createSite(db, site):
    """
    Return a site instance
    """
    return ElementStore.createElement(db, site)

  def updateSite(db, site):
    ElementStore.updateElement(db, site)
  
  def listItems(db, world_id):
    """
    Return a list of sites.
    """
    return ElementStore.getElements(db, ElementType.ITEM, world_id)

  def loadItem(db, id):
    """
    Return an item instance
    """
    return ElementStore.loadElement(db, id, Item())

  def createItem(db, item):
    """
    Return an Item instance
    """
    return ElementStore.createElement(db, item)
  
  def updateItem(db, item):
    ElementStore.updateElement(db, item)
     
    
def test():
  dir_name = os.path.dirname(__file__)
  path = os.path.join(dir_name, "schema.sql")
  db = sqlite3.connect("file::memory",
                        detect_types=sqlite3.PARSE_DECLTYPES)
  db.row_factory = sqlite3.Row
  with open(path) as f:
    db.executescript(f.read())

  world = World("world 1", "description", "details", '{ "dog": "kona" }')
  world = Elements.createWorld(db, world)
  world = World("world 2", "description", "details", '{ "dog": "kona" }')
  world = Elements.createWorld(db, world)

  character = Character(world.id, "char 1", "desc", "details")
  character = Elements.createCharacter(db, character)
  character = Character(world.id, "char 2", "desc", "details")
  character = Elements.createCharacter(db, character)

  site = Site(world.id, "site 1", "desc", "details")
  site = Elements.createSite(db, site)
  site = Site(world.id, "site 2", "desc", "details")
  site = Elements.createSite(db, site)

  item = Item(world.id, "item 1", "desc", "details")
  item = Elements.createItem(db, item)
  item = Item(world.id, "item 2", "desc", "details")
  item = Elements.createItem(db, item)
  
  print("list worlds")
  worlds = Elements.listWorlds(db)
  print(str(worlds))

  print("load world")
  world = Elements.loadWorld(db, world.id)
  print(str(world))

  print("list characters")
  characters = Elements.listCharacters(db, world.id)
  print(str(characters))

  print("load character")
  character = Elements.loadCharacter(db, characters[0]["id"])
  print(str(character))

  print("\nlist sites")
  sites = Elements.listSites(db, world.id)
  print(str(sites))

  print("\nload site")
  site = Elements.loadSite(db, sites[0]["id"])
  print(str(site))

  print("\nlist items")
  items = Elements.listItems(db, world.id)
  print(str(items))

  print("\nload item")
  item = Elements.loadItem(db, items[0]["id"])
  print(str(item))
  
  print("\nupdate item")
  item.description = "a new description"
  Elements.updateItem(db, item)
  item = Elements.loadItem(db, items[0]["id"])
  print(str(item))  
  db.close()


if __name__ == "__main__":
  test()

  
  

  
    

