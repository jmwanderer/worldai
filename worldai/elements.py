#!/usr/bin/env python3
"""
Represets the element of a world definition.
"""

import datetime
import os
import json
import logging
import enum
import pydantic
import typing

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

  @staticmethod
  def typeToName(element_type):
    return ElementType.typeNames[element_type]

  @staticmethod  
  def NoneType():
    return ElementType.typeToName(ElementType.NONE)

  @staticmethod  
  def WorldType():
    return ElementType.typeToName(ElementType.WORLD)

  @staticmethod  
  def CharacterType():
    return ElementType.typeToName(ElementType.CHARACTER)

  @staticmethod  
  def SiteType():
    return ElementType.typeToName(ElementType.SITE)

  @staticmethod  
  def ItemType():
    return ElementType.typeToName(ElementType.ITEM)


class CoreProps(str, enum.Enum):
  # Element properties not serialized in the DB
  PROP_ID = "id"  
  PROP_NAME = "name"

class CommonProps(pydantic.BaseModel):
  description: typing.Optional[str] = ""
  details: typing.Optional[str] = ""
  
class WorldProps(pydantic.BaseModel):
  description: typing.Optional[str] = ""
  details: typing.Optional[str] = ""
  plans: typing.Optional[str] = ""

class CharacterProps(pydantic.BaseModel):
  description: typing.Optional[str] = ""
  details: typing.Optional[str] = ""
  personality: typing.Optional[str] = ""

class ItemEffect(str, enum.Enum):
  # Possible effects of the item
  NONE = ""
  HEAL = "heal"  
  HURT = "hurt"
  PARALIZE = "paralize"
  POISON = "poison"
  SLEEP = "sleep"
  BRAINWASH = "brainwash"
  CAPTURE = "capture"
  INVISIBILITY = "invisibility"
  UNLOCK = "unlock"  

class ItemAbility(pydantic.BaseModel):
  effect: typing.Optional[ItemEffect] = ItemEffect.NONE
  site_id: typing.Optional[str] = ""
  
class ItemProps(pydantic.BaseModel):
  description: typing.Optional[str] = ""
  details: typing.Optional[str] = ""
  mobile: typing.Optional[bool] = True
  ability: typing.Optional[ItemAbility] = ItemAbility()

class SiteProps(pydantic.BaseModel):
  description: typing.Optional[str] = ""
  details: typing.Optional[str] = ""
  default_locked: typing.Optional[bool] = False

  
class IdName:
  """
  Contains the ID, name of an element.
  Used in list of elements.
  """
  def __init__(self, id, name):
    self.id = id;
    self.name = name

  def getID(self):
    return self.id

  def getName(self):
    return self.name

  def getJSON(self):
    return { "id": self.id,
             "name": self.name }

class ElemTag:
  """
  Contains the ID, type, and World ID of an element.
  Represents an informat set used between the client an server.
  (World ID and type can be looked up from the ID)

  The type field is the readable string, useful for GPT use.
  """
  def __init__(self, wid=None, id=None, element_type=ElementType.NONE):
    self.world_id = wid;    
    self.id = id;
    self.element_type = element_type

  def __eq__(self, other):
    if not isinstance(other, ElemTag):
      return False
    return (self.world_id == other.world_id and
            self.id == other.id and
            self.element_type == other.element_type)

  def getID(self):
    return self.id

  def getWorldID(self):
    return self.world_id

  def getType(self):
    """
    Return the type as a string
    """
    return self.element_type

  def noElement(self):
    return self.world_id is None

  def json(self):
    if self.world_id is None:
      return {}

    return {
      "wid": self.world_id,
      "element_type": self.element_type,
      "id": self.id,
    }
    
  def jsonStr(self):
    tag = self.json()
    return json.dumps(tag)

  def WorldTag(world_id):
    return ElemTag(world_id, world_id, ElementType.WorldType())

  def JsonTag(tag):
    if tag is None or tag.get("wid") is None:
      return ElemTag()
    return ElemTag(tag["wid"], tag["id"], tag["element_type"])
    
  
class Element:
  """
  Represents an element building block of a world
  """
  def __init__(self, element_type, parent_id):
    self.id = None
    self.type = element_type
    self.parent_id = parent_id
    self.name = None
    self.prop_model = None
    self.images = []  # List of image ids
    self.setProperties({})

  def getID(self):
    return self.id

  def hasImage(self):
    return len(self.images) > 0

  def getIdName(self):
    return IdName(self.id, self.name)

  def getElemTag(self):
    wid = self.parent_id if self.type != ElementType.WORLD else self.id
    return ElemTag(wid, self.id,
                   ElementType.typeToName(self.type))
  
  def setProperties(self, properties):
    """
    Set the set of encode properties.
    Override in derived classes
    """
    self.prop_model = CommonProps(**properties)

  def updateProperties(self, properties):
    """
    Change properties, including name, that are included.
    Do not remove properties.
    """
    if properties.get(CoreProps.PROP_NAME) is not None:
      self.name = properties[CoreProps.PROP_NAME]
      del properties[CoreProps.PROP_NAME]
    new_props = self.prop_model.model_dump()
    for key in properties.keys():
      new_props[key] = properties[key]
    self.setProperties(new_props)

  def getProperties(self):
    """
    Return dictonary of encoded properties
    """
    return self.prop_model.model_dump()

  def setPropertiesStr(self, properties):
    """
    Take an encoded json string of property values.
    """
    self.setProperties(json.loads(properties))

  def getPropertiesStr(self):
    """
    Return an encoded json string of property values.
    """
    return json.dumps(self.getProperties())

  def getAllProperties(self):
    """
    Return a map of properties including id and name,
    excluse internals of type and parent id.
    """
    return { CoreProps.PROP_ID: self.id,
             CoreProps.PROP_NAME: self.name,
             **self.getProperties() }

  def getName(self):
    return self.name

  def setName(self, name):
    self.name = name

  def getDescription(self):
    return self.prop_model.description

  def setDescription(self, value):
    self.prop_model.description = value
                       
  def getDetails(self):
    return self.prop_model.details

  def getDetailsHTML(self):
    return textToHTML(self.getDetails())

  def setDetails(self, value):
    self.prop_model.details = value

  def getImages(self):
    # Return a list of image ids
    return self.images

  def getImageByIndex(self, index):
    if len(self.images) == 0:
      return None
    
    index = max(0, min(index, len(self.images) - 1))
    return self.images[index]

  def __str__(self):
    type_str = ElementType.typeToName(self.type)
    propStr = json.dumps(self.getProperties())
    return (f"type: {self.type}, id: {self.id}, parent_id: {self.parent_id}, "
            + f"name: {self.name}, description: {self.getDescription()}, "
            + f"details: {self.getDetails()}")

def textToHTML(text):
  if text is None:
    return None
  return text.replace("\n\n","<p>").replace("\n","<br>")
                       

class World(Element):
  """
  Represents an instance of a World.
  """
  def __init__(self):
    super().__init__(ElementType.WORLD, '')

  def setProperties(self, properties):
    """
    Set the set of encode properties.
    Override base class
    """
    self.prop_model = WorldProps(**properties)
                       
  def getPlans(self):
    if self.prop_model.plans is None:
      return ""
    return self.prop_model.plans

  def getPlansHTML(self):
    return textToHTML(self.getPlans())
  
  def setPlans(self, value):
    self.prop_model.plans = value

    
class Character(Element):
  """
  Represents an instance of a Character.
  """
  def __init__(self, parent_id=''):
    super().__init__(ElementType.CHARACTER, parent_id)

  def setProperties(self, properties):
    """
    Set the set of encode properties.
    Override base class
    """
    self.prop_model = CharacterProps(**properties)

  def getPersonality(self):
    if self.prop_model.personality is None:
      return ""
    return self.prop_model.personality

  def getPersonalityHTML(self):
    return textToHTML(self.getPersonality())
  
  def setPersonality(self, value):
    self.prop_model.personality = value
    
    
class Site(Element):
  """
  Represents an instance of a Site
  """
  def __init__(self, parent_id=''):
    super().__init__(ElementType.SITE, parent_id)

  def setProperties(self, properties):
    """
    Set the set of encode properties.
    Override base class
    """
    self.prop_model = SiteProps(**properties)

  def getDefaultLocked(self):
    return self.prop_model.default_locked

  def setDefaultLocked(self, value):
    self.prop_model.default_locked =  value
    
class Item(Element):
  """
  Represents an instance of an Item
  """
  def __init__(self, parent_id=''):
    super().__init__(ElementType.ITEM, parent_id)
  
  def setProperties(self, properties):
    """
    Set the set of encode properties.
    Override base class
    """
    self.prop_model = ItemProps(**properties)
    
  def getIsMobile(self):
    return self.prop_model.mobile

  def setIsMobile(self, value):
    self.prop_model.mobile = value

  def getAbility(self):
    return self.prop_model.ability

  def setAbility(self, ability):
    self.prop_model.ability = ability

                       
class ElementStore:
  def loadElement(db, id, element):
    """
    Return an element insance
    """
    q = db.execute("SELECT parent_id, name, properties " +
                   "FROM elements WHERE id = ? and type = ?",
                   (id, element.type))
    r = q.fetchone()
    if r is None:
      return None

    element.id = id
    element.parent_id = r[0]
    element.name = r[1]      
    element.setPropertiesStr(r[2])

    c = db.execute("SELECT id FROM images WHERE parent_id = ? " +
                   "AND is_hidden = FALSE", (id,))
    for entry in c.fetchall():
      element.images.append(entry[0])
    return element

  def updateElement(db, element):
    q = db.execute("UPDATE elements SET  name = ?, properties = ? " +
                   "WHERE id = ? and type = ?",
                   (element.name, element.getPropertiesStr(),
                    element.id, element.type))
    db.commit()    
 
  def createElement(db, element):
    """
    Return an element insance
    """
    element.id = "id%s" % os.urandom(4).hex()
    q = db.execute("INSERT INTO elements (id, type, parent_id, name, " +
                   " properties) VALUES (?, ?, ?, ?, ?)",
                   (element.id, element.type, element.parent_id,
                    element.name, element.getPropertiesStr()))
    db.commit()
    return element
  
  def getElements(db, element_type, parent_id):
    """
    Return a list of elements: id and name
    """
    result = []
    q = db.execute("SELECT id, name FROM elements WHERE " +
                   "type = ? AND parent_id = ? AND is_hidden = FALSE",
                   (element_type, parent_id))
    for (id, name) in q.fetchall():
      result.append(IdName(id, name))

    return result

  def hideElement(db, element_type, id):
    db.execute("UPDATE elements SET is_hidden = TRUE WHERE id = ? AND " +
               "type = ?", (id, element_type))
    db.commit()

  def recoverElements(db, element_type, parent_id):
    c = db.cursor()      
    c.execute("UPDATE elements SET is_hidden = FALSE WHERE " +
               "parent_id = ? AND type = ? and is_hidden = TRUE",
               (parent_id, element_type))  
    db.commit()
    return c.rowcount
  

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

  def getThumbName(self):
    filename = self.getFilename()
    return filename[0:-4] + ".thmb" + filename[-4:]
  
def createImage(db, image):
  image.id = "id%s" % os.urandom(4).hex()
  db.execute("INSERT INTO images (id, parent_id, prompt, filename) " +
             "VALUES (?, ?, ?, ?)",
             (image.id, image.parent_id, image.prompt, image.filename))
  db.commit()
  return image

def getImageFromIndex(db, parent_id, index):
  # Convert index ordinal (0, 1, 2, ...) to an image id
  # TODO: Note this is probably broken and we need an ordering.
  images = listImages(db, parent_id)
  if len(images) > index:
    return images[index]["id"]
  return None
  
  
def hideImage(db, id):
  db.execute("UPDATE images SET is_hidden = TRUE WHERE id = ?", (id,))
  db.commit()

def recoverImages(db, parent_id):
  c = db.cursor()  
  c.execute("UPDATE images SET is_hidden = FALSE WHERE parent_id = ? " +
            "AND is_hidden = TRUE", (parent_id,))  
  db.commit()
  return c.rowcount

def getImageFile(db, data_dir, id):
  q = db.execute("SELECT filename FROM images WHERE id = ?", (id,))
  r = q.fetchone()
  if r is not None:
    filename = r[0]
    f = open(os.path.join(data_dir, filename), "rb")
    return f
  return None

def getImage(db, id):
  q = db.execute("SELECT parent_id, prompt, filename FROM images WHERE id = ?",
                 (id,))
  r = q.fetchone()
  if r is not None:
    image = Image(id)
    image.parent_id = r[0] 
    image.prompt = r[1]
    image.filename = r[2]    
    return image
  return None

def listImages(db, parent_id, include_hidden=False):
  result = []
  if include_hidden:
    q = db.execute("SELECT id, prompt, filename FROM images WHERE " +
                   "parent_id = ?", (parent_id,))
  else:
    q = db.execute("SELECT id, prompt, filename FROM images WHERE " +
                   "parent_id = ? AND is_hidden = FALSE", (parent_id,))
    
  for (id, prompt, filename) in q.fetchall():
    result.append({ "id": id,
                    "prompt": prompt,
                    "filename": filename })
  return result

def getImages(db, parent_id=None):
  """
  Return a list of image elements.
  If parent_id is None, return all images.
  Otherwise, return images for specified element.
  """
  result = []
  if parent_id is not None:
    q = db.execute("SELECT id, parent_id, prompt, filename FROM images " +
                   "WHERE parent_id = ? AND is_hidden = FALSE", (parent_id,))
  else:
    q = db.execute("SELECT id, parent_id, prompt, filename FROM images")
    
  for (id, parent_id, prompt, filename) in q.fetchall():
    image = Image(id)
    image.parent_id = parent_id
    image.prompt = prompt
    image.filename = filename    
    result.append(image)
  return result


def getElemTag(db, id):
  """
  Build an element tag from an id.
  Return null if not found
  """
  q = db.execute("SELECT parent_id, type from ELEMENTS where id = ?",
                 (id,))
  r = q.fetchone()
  if r is None:
      return None
  wid = r[0]
  type = r[1]
  if type == ElementType.WORLD:
    wid = id
  return ElemTag(wid, id, ElementType.typeToName(type))

def idNameToElemTag(db, idName):
  if idName is None:
    return None
  return getElemTag(db, idName.getID())

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

def hideCharacter(db, id):
  ElementStore.hideElement(db, ElementType.CHARACTER, id)

def recoverCharacters(db, world_id):
  return ElementStore.recoverElements(db, ElementType.CHARACTER, world_id)

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

def hideSite(db, id):
  ElementStore.hideElement(db, ElementType.SITE, id)

def recoverSites(db, world_id):
  return ElementStore.recoverElements(db, ElementType.SITE, world_id)
    
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

def hideItem(db, id):
  ElementStore.hideElement(db, ElementType.ITEM, id)

def recoverItems(db, world_id):
  return ElementStore.recoverElements(db, ElementType.ITEM, world_id)
    
def deleteImage(db, data_dir, image_id):
  image = getImage(db, image_id)
  
  db.execute("DELETE FROM images WHERE id = ?", (image_id,))
  db.commit()
  logging.info("remove image: %s",  image_id)  
  path = os.path.join(data_dir, image.filename)
  os.unlink(path)
  logging.info("delete file: %s", path)

def deleteCharacter(db, data_dir, id):
  character = loadCharacter(db, id)
  logging.info("delete character: [%s] %s",
               character.id,
               character.getName())
  images = listImages(db, id, include_hidden=True)

  for image in images:
    deleteImage(db, data_dir, image["id"])
    
  db.execute("DELETE FROM elements WHERE id = ? AND type = ?",
            (id, ElementType.CHARACTER))
  db.commit()

def deleteWorld(db, data_dir, world_id):
  world = loadWorld(db, world_id)
  logging.info("delete world: [%s] %s",  world.id, world.getName())
  characters = listCharacters(db, world.id)
  for entry in characters:
    deleteCharacter(db, data_dir, entry.getID())

  images = listImages(db, world.id, include_hidden=True)    
  for image in images:
    deleteImage(db, data_dir, image["id"])
    
  db.execute("DELETE FROM elements WHERE id = ? AND type = ?",
               (world.id, ElementType.WORLD))
  db.commit()

  
def getAdjacentElements(id_name, id_name_list):
  """
  Return (prev, next) IdName entries for the given IdName in the list
  """
  index = 0
  for entry in id_name_list:
    if entry.getID() == id_name.getID():
      break
    index += 1

  prev_entry = None
  next_entry = None

  if index < len(id_name_list):
    if index > 0:
      prev_entry = id_name_list[index - 1]
    if index < len(id_name_list) - 1:
      next_entry = id_name_list[index + 1]

  return (prev_entry, next_entry)
    

