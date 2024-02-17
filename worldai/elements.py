#!/usr/bin/env python3
"""
Represets the element of a world definition.
"""

import enum
import json
import logging
import os
import typing
from typing import Optional

import pydantic


# Types for IDs
ElemID = typing.NewType('ElemID', str)
WorldID = typing.NewType('WorldID', ElemID)


class ElementType(int, enum.Enum):
    # Used for storage into DB
    NONE = 0
    WORLD = 1
    CHARACTER = 2
    SITE = 3
    ITEM = 4
    DOCUMENT = 5

class ElementTypeStr(str, enum.Enum):
    """
    Types of elements in a world.
    """
    NONE = "None"
    WORLD = "World"
    CHARACTER = "Character"
    SITE = "Site"
    ITEM = "Item"
    DOCUMENT = "Document"

class ElementTypes:
    @staticmethod
    def _typeToName(element_type: ElementType) -> ElementTypeStr:
        if element_type == ElementType.WORLD:
            return ElementTypeStr.WORLD
        if element_type == ElementType.CHARACTER:
            return ElementTypeStr.CHARACTER
        if element_type == ElementType.SITE:
            return ElementTypeStr.SITE
        if element_type == ElementType.ITEM:
            return ElementTypeStr.ITEM
        if element_type == ElementType.DOCUMENT:
            return ElementTypeStr.DOCUMENT
        return ElementTypeStr.NONE

    @staticmethod
    def NoneType() -> ElementTypeStr:
        return ElementTypes._typeToName(ElementType.NONE)

    @staticmethod
    def WorldType() -> ElementTypeStr:
        return ElementTypes._typeToName(ElementType.WORLD)

    @staticmethod
    def DocumentType() -> ElementTypeStr:
        return ElementTypes._typeToName(ElementType.DOCUMENT)

    @staticmethod
    def CharacterType() -> ElementTypeStr:
        return ElementTypes._typeToName(ElementType.CHARACTER)

    @staticmethod
    def SiteType() -> ElementTypeStr:
        return ElementTypes._typeToName(ElementType.SITE)

    @staticmethod
    def ItemType() -> ElementTypeStr:
        return ElementTypes._typeToName(ElementType.ITEM)


class CoreProps(str, enum.Enum):
    # Element properties not serialized in the DB
    PROP_ID = "id"
    PROP_NAME = "name"


class WorldProps(pydantic.BaseModel):
    description: typing.Optional[str] = ""
    details: typing.Optional[str] = ""
    plans: typing.Optional[str] = ""


class DocSection(pydantic.BaseModel):
    heading: typing.Optional[str] = ""
    text: typing.Optional[str] = ""


class DocProps(pydantic.BaseModel):
    sections: typing.List[DocSection] = []


class CharacterProps(pydantic.BaseModel):
    description: typing.Optional[str] = ""
    details: typing.Optional[str] = ""
    personality: typing.Optional[str] = ""


class ItemEffect(str, enum.Enum):
    # Possible effects of the item
    OTHER = ""
    NONE = "none"
    HEAL = "heal"
    HURT = "hurt"
    PARALIZE = "paralize"
    POISON = "poison"
    SLEEP = "sleep"
    BRAINWASH = "brainwash"
    CAPTURE = "capture"
    INVISIBILITY = "invisibility"
    OPEN = "open"


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
    default_open: typing.Optional[bool] = True


class IdName:
    """
    Contains the ID, name of an element.
    Used in list of elements.
    """

    def __init__(self, eid: ElemID, name: str):
        self.eid = eid
        self.name = name

    def getID(self) -> ElemID:
        return self.eid

    def getName(self) -> str:
        return self.name

    def getJSON(self) -> dict:
        return {"id": self.eid, "name": self.name}


class ElemTag:
    """
    Contains the ID, type, and World ID of an element.
    Represents an informat set used between the client an server.
    (World ID and type can be looked up from the ID)

    The type field is the readable string, useful for GPT use.
    """

    def __init__(self, 
                 wid: WorldID = WorldID(ElemID("")), 
                 eid: ElemID = ElemID(""), 
                 element_type : ElementTypeStr = ElementTypeStr.NONE):
        self.world_id = wid
        self.eid = eid
        self.element_type = element_type

    def __eq__(self, other):
        if not isinstance(other, ElemTag):
            return False
        return (
            self.world_id == other.world_id
            and self.eid == other.eid
            and self.element_type == other.element_type
        )

    def getID(self) -> ElemID:
        return self.eid

    def getWorldID(self) -> WorldID:
        return self.world_id

    def getType(self) -> ElementTypeStr:
        """
        Return the type as a string
        """
        return self.element_type

    def noElement(self) -> bool:
        return self.world_id is None

    def json(self) -> dict:
        if self.world_id is None:
            return {}

        return {
            "wid": self.world_id,
            "element_type": self.element_type,
            "id": self.eid,
        }

    def jsonStr(self) -> str:
        tag = self.json()
        return json.dumps(tag)

    @staticmethod
    def WorldTag(world_id):
        return ElemTag(world_id, world_id, ElementTypes.WorldType())

    @staticmethod
    def JsonTag(tag):
        if tag is None or tag.get("wid") is None:
            return ElemTag()
        return ElemTag(tag["wid"], tag["id"], tag["element_type"])


class Element:
    """
    Represents an element building block of a world
    """

    def __init__(self, element_type, parent_id):
        self.eid = None
        self.type = element_type
        self.parent_id = parent_id
        self.name = None
        self.prop_model = None
        self.images = []  # List of image ids
        self._setProperties({})

    def getID(self):
        return self.eid

    def hasImage(self):
        return len(self.images) > 0

    def getIdName(self):
        return IdName(self.eid, self.name)

    def getElemTag(self):
        wid = self.parent_id if self.type != ElementType.WORLD else self.eid
        return ElemTag(wid, self.eid, ElementTypes._typeToName(self.type))

    def _fixProperties(self, properties):
        """
        Update any properties that need to change for backwards compatibility
        and migration
        """
        return properties

    def _setProperties(self, properties):
        """
        Set the set of encode properties.
        Override in derived classes
        """
        # Never used
        self.prop_model = {**properties}

    def updateProperties(self, properties):
        """
        Change properties, including name, that are included.
        Do not remove properties.
        """
        if properties.get(CoreProps.PROP_NAME) is not None:
            self.name = properties[CoreProps.PROP_NAME]
            del properties[CoreProps.PROP_NAME]
        new_props = self._getProperties()
        for key in properties.keys():
            new_props[key] = properties[key]
        self._setProperties(new_props)

    def _getProperties(self):
        """
        Return dictonary of encoded properties
        """
        return self.prop_model.model_dump()

    def setPropertiesStr(self, properties):
        """
        Take an encoded json string of property values.
        """
        properties = self._fixProperties(json.loads(properties))
        self._setProperties(properties)

    def getPropertiesStr(self):
        """
        Return an encoded json string of property values.
        """
        return json.dumps(self._getProperties())

    def getAllProperties(self):
        """
        Return a map of properties including id and name,
        excluse internals of type and parent id.
        """
        return {
            CoreProps.PROP_ID: self.eid,
            CoreProps.PROP_NAME: self.name,
            **self._getProperties(),
        }

    def getName(self):
        return self.name

    def setName(self, name):
        self.name = name

    def getDescription(self):
        if hasattr(self.prop_model, "description"):
            return self.prop_model.description
        return ""

    def setDescription(self, value):
        if hasattr(self.prop_model, "description"):
            self.prop_model.description = value

    def getDetails(self):
        if hasattr(self.prop_model, "details"):
            return self.prop_model.details
        return ""

    def getDetailsHTML(self):
        return textToHTML(self.getDetails())

    def setDetails(self, value):
        if hasattr(self.prop_model, "details"):
            self.prop_model.details = value

    def getInfoText(self):
        content = self.getName()
        if self.getDescription() is not None:
            content = content + ": " + self.getDescription()
        if self.getDetails() is not None:
            content = content + "\n" + self.getDetails()
        return [(0, content)]

    def getImages(self):
        # Return a list of image ids
        return self.images

    def getImageByIndex(self, index):
        if len(self.images) == 0:
            return None

        index = max(0, min(index, len(self.images) - 1))
        return self.images[index]

    def __str__(self):
        return (
            f"type: {self.type}, id: {self.eid}, parent_id: {self.parent_id}, "
            + f"name: {self.name}, description: {self.getDescription()}, "
            + f"details: {self.getDetails()}"
        )


def textToHTML(text):
    if text is None:
        return None
    return text.replace("\n\n", "<p>").replace("\n", "<br>")


class World(Element):
    """
    Represents an instance of a World.
    """

    def __init__(self):
        super().__init__(ElementType.WORLD, "")

    def _setProperties(self, properties):
        """
        Set the set of encode properties.
        Override base class
        """
        self.prop_model = WorldProps(**properties)

    def _fixProperties(self, properties):
        if properties.get("notes") is not None:
            del properties["notes"]
        return properties

    def getPlans(self):
        if self.prop_model.plans is None:
            return ""
        return self.prop_model.plans

    def getPlansHTML(self):
        return textToHTML(self.getPlans())

    def setPlans(self, value):
        self.prop_model.plans = value


class Document(Element):
    """
    Represents a document associated with a world
    """

    def __init__(self, parent_id=""):
        super().__init__(ElementType.DOCUMENT, parent_id)

    def _setProperties(self, properties):
        """
        Set the set of encode properties.
        Override base class
        """
        self.prop_model = DocProps(**properties)

    def _fixProperties(self, properties):
        if properties.get("abstact") is not None:
            del properties["abstract"]
        if properties.get("outline") is not None:
            del properties["outline"]
        return properties

    def getSectionList(self):
        return [x.heading for x in self.prop_model.sections]

    def addSection(self, heading: str, text: str):
        if not heading in self.getSectionList():
            section = DocSection(heading=heading, text=text)
            self.prop_model.sections.append(section)

    def getSectionText(self, heading: str) -> Optional[str]:
        for section in self.prop_model.sections:
            if section.heading == heading:
                return section.text
        return None

    def updateSection(self, heading: str, text: str):
        for section in self.prop_model.sections:
            if section.heading == heading:
                section.text = text
                break

    def updateHeading(self, heading: str, new_heading: str):
        for section in self.prop_model.sections:
            if section.heading == heading:
                section.heading = new_heading
                break

    def getInfoText(self):
        """
        Return entries of (index, text)
        """
        count = 0
        for section in self.prop_model.sections:
            count += 1
            yield ((count, section.heading + " : " + section.text))


class Character(Element):
    """
    Represents an instance of a Character.
    """

    def __init__(self, parent_id=""):
        super().__init__(ElementType.CHARACTER, parent_id)

    def _setProperties(self, properties):
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

    def __init__(self, parent_id=""):
        super().__init__(ElementType.SITE, parent_id)

    def _fixProperties(self, properties):
        if properties.get("locked") is not None:
            properties["default_open"] = not properties["locked"]
            del properties["locked"]
        return properties

    def _setProperties(self, properties):
        """
        Set the set of encode properties.
        Override base class
        """
        self.prop_model = SiteProps(**properties)

    def getDefaultOpen(self):
        return self.prop_model.default_open

    def setDefaultOpen(self, value):
        self.prop_model.default_open = value


class Item(Element):
    """
    Represents an instance of an Item
    """

    def __init__(self, parent_id=""):
        super().__init__(ElementType.ITEM, parent_id)

    def _fixProperties(self, properties):
        if properties.get("ability") is not None:
            if properties["ability"].get("effect") is not None:
                if properties["ability"]["effect"] == "unlock":
                    properties["ability"]["effect"] = "open"
                if properties["ability"]["effect"] == "":
                    properties["ability"]["effect"] = "none"
        return properties

    def _setProperties(self, properties):
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
    @staticmethod
    def loadElement(db, eid, element):
        """
        Return an element insance
        """
        q = db.execute(
            "SELECT parent_id, name, properties "
            + "FROM elements WHERE id = ? and type = ?",
            (eid, element.type),
        )
        r = q.fetchone()
        if r is None:
            return None

        element.eid = eid
        element.parent_id = r[0]
        element.name = r[1]
        element.setPropertiesStr(r[2])

        c = db.execute(
            "SELECT id FROM images WHERE parent_id = ? " + "AND is_hidden = FALSE",
            (eid,),
        )
        for entry in c.fetchall():
            element.images.append(entry[0])
        return element

    @staticmethod
    def findElement(db, pid, name, element):
        """
        Return an element id
        """
        q = db.execute(
            "SELECT id FROM elements WHERE "
            + "name LIKE ? "
            + "AND parent_id = ? AND type = ?",
            (name, pid, element.type),
        )
        r = q.fetchone()
        if r is None:
            return None

        return ElementStore.loadElement(db, r[0], element)

    @staticmethod
    def updateElement(db, element):
        db.execute(
            "UPDATE elements SET  name = ?, properties = ? "
            + "WHERE id = ? and type = ?",
            (element.name, element.getPropertiesStr(), element.eid, element.type),
        )
        db.commit()

    @staticmethod        
    def createElement(db, element):
        """
        Return an element insance
        """
        element.eid = "id%s" % os.urandom(4).hex()
        db.execute(
            "INSERT INTO elements (id, type, parent_id, name, "
            + " properties) VALUES (?, ?, ?, ?, ?)",
            (
                element.eid,
                element.type,
                element.parent_id,
                element.name,
                element.getPropertiesStr(),
            ),
        )
        db.commit()
        return element

    @staticmethod
    def getElements(db, element_type, parent_id):
        """
        Return a list of elements: eid and name
        """
        result = []
        q = db.execute(
            "SELECT id, name FROM elements WHERE "
            + "type = ? AND parent_id = ? AND is_hidden = FALSE",
            (element_type, parent_id),
        )
        for eid, name in q.fetchall():
            result.append(IdName(eid, name))

        return result

    @staticmethod
    def hideElement(db, element, wid, name):
        instance = ElementStore.findElement(db, wid, name, element)
        if instance is not None:
            c = db.cursor()
            c.execute(
                "UPDATE elements SET is_hidden = TRUE WHERE id = ? AND " + "type = ?",
                (instance.eid, element.type),
            )
            db.commit()
            return c.rowcount
        return 0

    @staticmethod
    def recoverElements(db, element_type, parent_id):
        c = db.cursor()
        c.execute(
            "UPDATE elements SET is_hidden = FALSE WHERE "
            + "parent_id = ? AND type = ? and is_hidden = TRUE",
            (parent_id, element_type),
        )
        db.commit()
        return c.rowcount


class Image:
    """
    The image class represents an image attached to a particular element.

    """

    def __init__(self, iid=None):
        self.iid = iid
        self.filename = None
        self.prompt = None
        self.parent_id = None

    def getID(self):
        return self.iid

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
    image.iid = "id%s" % os.urandom(4).hex()
    db.execute(
        "INSERT INTO images (id, parent_id, prompt, filename) " + "VALUES (?, ?, ?, ?)",
        (image.iid, image.parent_id, image.prompt, image.filename),
    )
    db.commit()
    return image


def getImageFromIndex(db, parent_id, index):
    # Convert index ordinal (0, 1, 2, ...) to an image id
    # TODO: Note this is probably broken and we need an ordering.
    images = listImages(db, parent_id)
    if len(images) > index:
        return images[index]["id"]
    return None


def hideImage(db, iid):
    db.execute("UPDATE images SET is_hidden = TRUE WHERE id = ?", (iid,))
    db.commit()


def recoverImages(db, parent_id):
    c = db.cursor()
    c.execute(
        "UPDATE images SET is_hidden = FALSE WHERE parent_id = ? "
        + "AND is_hidden = TRUE",
        (parent_id,),
    )
    db.commit()
    return c.rowcount


def getImageFile(db, data_dir, iid):
    q = db.execute("SELECT filename FROM images WHERE id = ?", (iid,))
    r = q.fetchone()
    if r is not None:
        filename = r[0]
        f = open(os.path.join(data_dir, filename), "rb")
        return f
    return None


def getImage(db, iid):
    q = db.execute("SELECT parent_id, prompt, filename FROM images WHERE id = ?", (iid,))
    r = q.fetchone()
    if r is not None:
        image = Image(iid)
        image.parent_id = r[0]
        image.prompt = r[1]
        image.filename = r[2]
        return image
    return None


def listImages(db, parent_id, include_hidden=False):
    result = []
    if include_hidden:
        q = db.execute(
            "SELECT id, prompt, filename FROM images WHERE " + "parent_id = ?",
            (parent_id,),
        )
    else:
        q = db.execute(
            "SELECT id, prompt, filename FROM images WHERE "
            + "parent_id = ? AND is_hidden = FALSE",
            (parent_id,),
        )

    for iid, prompt, filename in q.fetchall():
        result.append({"id": iid, "prompt": prompt, "filename": filename})
    return result


def getImages(db, parent_id=None):
    """
    Return a list of image elements.
    If parent_id is None, return all images.
    Otherwise, return images for specified element.
    """
    result = []
    if parent_id is not None:
        q = db.execute(
            "SELECT id, parent_id, prompt, filename FROM images "
            + "WHERE parent_id = ? AND is_hidden = FALSE",
            (parent_id,),
        )
    else:
        q = db.execute("SELECT id, parent_id, prompt, filename FROM images")

    for iid, pid, prompt, filename in q.fetchall():
        image = Image(iid)
        image.parent_id = pid
        image.prompt = prompt
        image.filename = filename
        result.append(image)
    return result


def getElemTag(db, eid):
    """
    Build an element tag from an id.
    Return null if not found
    """
    q = db.execute("SELECT parent_id, type from ELEMENTS where id = ?", (eid,))
    r = q.fetchone()
    if r is None:
        return None
    wid = r[0]
    etype = r[1]
    if etype == ElementType.WORLD:
        wid = eid
    return ElemTag(wid, eid, ElementTypes._typeToName(etype))


def idNameToElemTag(db, idName):
    if idName is None:
        return None
    return getElemTag(db, idName.getID())


def listWorlds(db):
    """
    Return a list of worlds.
    """
    return ElementStore.getElements(db, ElementType.WORLD, "")


def loadWorld(db, eid: str) -> Optional[World]:
    """
    Return a world instance
    """
    return ElementStore.loadElement(db, eid, World())


def findWorld(db, name: str) -> Optional[World]:
    """
    Return a world instance by name
    """
    element = World()
    q = db.execute(
        "SELECT id FROM elements WHERE " + "name LIKE ? AND type = ?",
        (name, element.type),
    )
    r = q.fetchone()
    if r is None:
        return None

    return loadWorld(db, r[0])


def createWorld(db, world: World) -> World:
    """
    Return a world instance
    """
    return ElementStore.createElement(db, world)


def updateWorld(db, world: World):
    ElementStore.updateElement(db, world)


def createDocument(db, document: Document) -> Document:
    """
    Return a document instance
    """
    return ElementStore.createElement(db, document)


def listDocuments(db, world_id: str):
    return ElementStore.getElements(db, ElementType.DOCUMENT, world_id)


def loadDocument(db, eid) -> Optional[Document]:
    return ElementStore.loadElement(db, eid, Document())


def findDocument(db, wid: str, name: str) -> Optional[Document]:
    return ElementStore.findElement(db, wid, name, Document())


def updateDocument(db, document: Document):
    ElementStore.updateElement(db, document)


def listCharacters(db, world_id):
    """
    Return a list of characters.
    """
    return ElementStore.getElements(db, ElementType.CHARACTER, world_id)


def loadCharacter(db, eid: str) -> Optional[Character]:
    """
    Return a character instance
    """
    return ElementStore.loadElement(db, eid, Character())


def findCharacter(db, wid: str, name: str) -> Optional[Character]:
    """
    Return a character instance by name
    """
    return ElementStore.findElement(db, wid, name, Character())


def createCharacter(db, character: Character) -> Character:
    """
    Return a character instance
    """
    return ElementStore.createElement(db, character)


def updateCharacter(db, character: Character):
    ElementStore.updateElement(db, character)


def hideCharacter(db, wid: str, name: str) -> int:
    count = ElementStore.hideElement(db, Character(), wid, name)
    return count == 1


def recoverCharacters(db, world_id: str) -> int:
    return ElementStore.recoverElements(db, ElementType.CHARACTER, world_id)


def listSites(db, world_id):
    """
    Return a list of sites.
    """
    return ElementStore.getElements(db, ElementType.SITE, world_id)


def loadSite(db, eid: str) -> Optional[Site]:
    """
    Return a site instance
    """
    return ElementStore.loadElement(db, eid, Site())


def findSite(db, pid: str, name: str) -> Optional[Site]:
    """
    Return a site instance by name
    """
    return ElementStore.findElement(db, pid, name, Site())


def createSite(db, site: Site) -> Site:
    """
    Return a site instance
    """
    return ElementStore.createElement(db, site)


def updateSite(db, site: Site):
    ElementStore.updateElement(db, site)


def hideSite(db, wid: str, name: str) -> int:
    count = ElementStore.hideElement(db, Site(), wid, name)
    return count == 1


def recoverSites(db, world_id: str) -> int:
    return ElementStore.recoverElements(db, ElementType.SITE, world_id)


def listItems(db, world_id):
    """
    Return a list of sites.
    """
    return ElementStore.getElements(db, ElementType.ITEM, world_id)


def loadItem(db, eid: str) -> Optional[Item]:
    """
    Return an item instance
    """
    return ElementStore.loadElement(db, eid, Item())


def findItem(db, pid: str, name: str) -> Optional[Item]:
    """
    Return an item instance by name
    """
    return ElementStore.findElement(db, pid, name, Item())


def createItem(db, item: Item) -> Item:
    """
    Return an Item instance
    """
    return ElementStore.createElement(db, item)


def updateItem(db, item: Item):

    ElementStore.updateElement(db, item)


def hideItem(db, wid: str, name: str) -> int:
    count = ElementStore.hideElement(db, Item(), wid, name)
    return count == 1


def recoverItems(db, world_id: str) -> int:
    return ElementStore.recoverElements(db, ElementType.ITEM, world_id)


def deleteImage(db, data_dir, image_id):
    image = getImage(db, image_id)

    db.execute("DELETE FROM images WHERE id = ?", (image_id,))
    db.commit()
    logging.info("remove image: %s", image_id)
    path = os.path.join(data_dir, image.filename)
    os.unlink(path)
    logging.info("delete file: %s", path)


def deleteCharacter(db, data_dir, eid):
    character = loadCharacter(db, eid)
    logging.info("delete character: [%s] %s", character.eid, character.getName())
    images = listImages(db, eid, include_hidden=True)

    for image in images:
        deleteImage(db, data_dir, image["id"])

    db.execute(
        "DELETE FROM elements WHERE id = ? AND type = ?", (eid, ElementType.CHARACTER)
    )
    db.commit()


def deleteWorld(db, data_dir, world_id):
    world = loadWorld(db, world_id)
    logging.info("delete world: [%s] %s", world.eid, world.getName())
    characters = listCharacters(db, world.eid)
    for entry in characters:
        deleteCharacter(db, data_dir, entry.getID())

    images = listImages(db, world.eid, include_hidden=True)
    for image in images:
        deleteImage(db, data_dir, image["id"])

    db.execute(
        "DELETE FROM elements WHERE id = ? AND type = ?", (world.eid, ElementType.WORLD)
    )
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
