#!/usr/bin/env python3
"""
Represets the element of a world definition.
"""

import datetime
import os
import json

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


# Malable properties that an element may have
PROP_NAME = "name"
PROP_DESCRIPTION = "description"
PROP_DETAILS = "details"
  

class Element:
  """
  Represents an element building block of a world
  """
  def __init__(self, element_type, parent_id):
    self.id = None
    self.type = element_type
    self.parent_id = parent_id
    self.name = None
    self.properties = {}

  def myProps(self):
    return [ PROP_NAME, PROP_DESCRIPTION, PROP_DETAILS ]
  
  def setProperties(self, properties):
    """
    Set malable properties from a dictionary
    """
    self.properties = {}
    self.updateProperties(properties)

  def updateProperties(self, properties):
    for prop_name in properties.keys():
      if prop_name in self.myProps():
        self.setProperty(prop_name, properties[prop_name])
    
  def getProperties(self):
    """
    Return dictonary of malable properties
    """
    return { PROP_NAME: self.name, **self.properties }

  def setPropertiesJSON(self, properties):
    """
    Take an encoded json string of property values.
    Can take name in the string
    """
    self.setProperties(json.loads(properties))

  def getPropertiesJSON(self):
    """
    Return an encoded json string of property values.
    Will not include id, parent_id, type, or name
    """
    return json.dumps(self.properties)

  def getProperty(self, name):
    if name == PROP_NAME:
      return self.name
    return self.properties.get(name, None)
  
  def setProperty(self, name, value):
    if name == PROP_NAME:
      self.name = value
    else:
      self.properties[name] = value

  def getName(self):
    return self.name

  def setName(self, name):
    self.name = name

  def getDescription(self):
    return self.getProperty(PROP_DESCRIPTION)

  def getDetails(self):
    return self.getProperty(PROP_DETAILS)

  def setDescription(self, value):
    return self.setProperty(PROP_DESCRIPTION, value)

  def setDetails(self, value):
    return self.setProperty(PROP_DETAILS, value)
  

  def __str__(self):
    type_str = ElementType.typeToName(self.type)
    propStr = json.dumps(self.getProperties())
    return (f"type: {self.type}, id: {self.id}, parent_id: {self.parent_id}, "
            + f"name: {self.name}, description: {self.getDescription()}, "
            + f"details: {self.getDetails()}")
                       
class World(Element):
  """
  Represents an instance of a World.
  """
  def __init__(self):
    super().__init__(ElementType.WORLD, '')

    
class Character(Element):
  """
  Represents an instance of a Character.
  """
  def __init__(self, parent_id=''):
    super().__init__(ElementType.CHARACTER, parent_id)
    
class Site(Element):
  """
  Represents an instance of a Site
  """
  def __init__(self, parent_id=''):
    super().__init__(ElementType.SITE, parent_id)

class Item(Element):
  """
  Represents an instance of an Item
  """
  def __init__(self, parent_id=''):
    super().__init__(ElementType.ITEM, parent_id)

                       
class ElementStore:
  def loadElement(db, id, element):
    """
    Return an element insance
    """
    q = db.execute("SELECT parent_id, name, properties " +
                   "FROM elements WHERE id = ? and type = ?",
                   (id, element.type))
    r = q.fetchone()
    if r is not None:
      element.id = id
      element.parent_id = r[0]
      element.name = r[1]      
      element.setPropertiesJSON(r[2])
      return element
    return None

  def updateElement(db, element):
    q = db.execute("UPDATE elements SET  name = ?, properties = ? " +
                   "WHERE id = ? and type = ?",
                   (element.name, element.getPropertiesJSON(),
                    element.id, element.type))
    db.commit()    
 
  def createElement(db, element):
    """
    Return an element insance
    """
    element.id = "id%s" % os.urandom(4).hex()
    q = db.execute("INSERT INTO elements VALUES (?, ?, ?, ?, ?)",
                   (element.id, element.type, element.parent_id,
                    element.name, element.getPropertiesJSON()))
    db.commit()
    return element
  
  def getElements(db, element_type, parent_id):
    """
    Return a list of elements: id and name
    """
    result = []
    q = db.execute("SELECT id, name FROM elements WHERE " +
                   "type = ? AND parent_id = ?", (element_type, parent_id))
    for (id, name) in q.fetchall():
      result.append({ "id": id, PROP_NAME :  name })

    return result

class Image:
  """
  The image class represents an image attached to a particular element.
  
  """
  def __init__(self, id=None):
    self.id = id
    self.filename = None
    self.prompt = None
    self.parent_id = None

  def setPrompt(self, prompt):
    self.prompt = prompt

  def setParentId(self, parent_id):
    self.parent_id = parent_id
    
  def getFilename(self):
    if self.filename is None:
      self.filename = os.urandom(12).hex() + ".png"
    return self.filename
  
def createImage(db, image):
  image.id = "id%s" % os.urandom(4).hex()
  db.execute("INSERT INTO images VALUES (?, ?, ?, ?)",
             (image.id, image.parent_id, image.prompt, image.filename))
  db.commit()
  return image

def getImageFile(db, data_dir, id):
  q = db.execute("SELECT filename FROM images WHERE id = ?", (id,))
  r = q.fetchone()
  if r is not None:
    filename = r[0]
    f = open(os.path.join(data_dir, filename), "rb")
    return f
  return None

def listImages(db, parent_id):
  result = []
  q = db.execute("SELECT id, prompt, filename FROM images WHERE parent_id = ?", (parent_id,))
  for (id, prompt, filename) in q.fetchall():
    result.append({ "id": id,
                    "prompt": prompt,
                    "filename": filename })
  return result

def listWorlds(db):
  """
  Return a list of worlds.
  """
  return ElementStore.getElements(db, ElementType.WORLD, '')


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
    

  
  

  
    

