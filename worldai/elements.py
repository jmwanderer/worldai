"""
Represets the element of a world definition.

    Worlds, Characters, Sites, Items, Documents

    Jim Wanderer
    http://github.com/jmwanderer
"""

import enum
import io
import json
import logging
import os
import typing
from typing import Optional

import pydantic

# Types for IDs
ElemID = typing.NewType("ElemID", str)
WorldID = typing.NewType("WorldID", ElemID)
ELEM_ID_NONE = ElemID("")
WORLD_ID_NONE = WorldID(ELEM_ID_NONE)
PLAYER_ID = ElemID("id0")


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


class BaseProps(pydantic.BaseModel):
    description: str = ""
    details: str = ""


class CharStatus(str, enum.Enum):
    # Possible states of characters
    NONE = "none"
    SLEEPING = "sleeping"
    PARALIZED = "paralized"
    POISONED = "poisoned"
    BRAINWASHED = "brainwashed"
    CAPTURED = "captured"
    INVISIBLE = "invisible"
    INJURED = "injured"
    DEAD = "dead"

class ConditionVerb(str, enum.Enum):
    NONE = "none"
    AT = "at"
    HAS = "has"
    IS = "is"
    USES = "uses"

class ConditionProp(pydantic.BaseModel):
    """
    Describes a start or end condition.
    WHO - WHAT, WHO - WHERE, WHAT - WHERE
    TODO: consider including the player in these conditions. Player as a character
    Start:
        - character at location
        - character has item
        - character is CharStatus
        - item at location
    End:
        - start conditions, plus:
        - character uses item
        - character uses item on character - TODO
    """
    # condition defines which other fields are valid
    # meaning given by combination of IDs set and condition verb
    verb: ConditionVerb = ConditionVerb.NONE
    char_id: ElemID = ELEM_ID_NONE
    char_status: CharStatus = CharStatus.NONE
    item_id: ElemID = ELEM_ID_NONE
    site_id: ElemID = ELEM_ID_NONE
    target_char_id: ElemID = ELEM_ID_NONE

class Condition:
    """
    Utility functions for working with conditions.
    Consider this the set of valid conditions
    """
    @staticmethod
    def characterUses(char_id: ElemID, item_id: ElemID) -> ConditionProp:
        return ConditionProp(char_id=char_id, verb=ConditionVerb.USES, item_id=item_id)

    @staticmethod
    def characterAt(char_id: ElemID, site_id: ElemID) -> ConditionProp:
        return ConditionProp(char_id=char_id, verb=ConditionVerb.AT, site_id=site_id)

    @staticmethod
    def characterHas(char_id: ElemID, item_id: ElemID) -> ConditionProp:
        return ConditionProp(char_id=char_id, verb=ConditionVerb.HAS, item_id=item_id)

    @staticmethod
    def itemAt(item_id: ElemID, site_id: ElemID) -> ConditionProp:
        return ConditionProp(item_id=item_id, verb=ConditionVerb.AT, site_id=site_id)

    @staticmethod
    def characterIs(char_id: ElemID, char_status: CharStatus) -> ConditionProp:
        return ConditionProp(char_id=char_id, verb=ConditionVerb.IS, char_status=char_status)

    @staticmethod
    def makeProps(verb: ConditionVerb, char_id: ElemID, item_id: ElemID, site_id: ElemID, state: str = "") -> list[ConditionProp]:
        """
        Make valid condition properties from the 5 possible input values.
        One set of values can create multiple properties
        If the input values don't make sense, an empty list is returned.
        Note: we don't try to catch information that will be ignored. This is matched to the values that we see the
        GPT setting in the action calls
        """
        props = []
        if verb == ConditionVerb.AT:
            if char_id != ELEM_ID_NONE and site_id != ELEM_ID_NONE:
                props.append(Condition.characterAt(char_id, site_id))
                # item id may also be set
                if item_id != ELEM_ID_NONE:
                    props.append(Condition.characterHas(char_id, item_id))
            elif item_id != ELEM_ID_NONE and site_id != ELEM_ID_NONE:
                props.append(Condition.itemAt(item_id, site_id))

        elif verb == ConditionVerb.HAS:
            if char_id != ELEM_ID_NONE and item_id != ELEM_ID_NONE:
                props.append(Condition.characterHas(char_id, item_id))
                # site id may also be set
                if site_id != ELEM_ID_NONE:
                    props.append(Condition.characterAt(char_id, site_id))

        elif verb == ConditionVerb.IS:
            if char_id != ELEM_ID_NONE and len(state) > 0:
                char_status: CharStatus = CharStatus.NONE
                if state == "sleeping":
                    char_status = CharStatus.SLEEPING
                elif state == "poisoned":
                    char_status = CharStatus.POISONED
                elif state == "paralized":
                    char_status = CharStatus.PARALIZED
                elif state == "injured":
                    char_status = CharStatus.INJURED
                elif state == "invisible":
                    char_status = CharStatus.INVISIBLE
                elif state == "captured":
                    char_status = CharStatus.CAPTURED
                elif state == "dead":
                    char_status = CharStatus.DEAD
                if char_status != CharStatus.NONE:
                    props.append(Condition.characterIs(char_id, char_status))

        elif verb == ConditionVerb.USES:
            if char_id != ELEM_ID_NONE:
                if item_id != ELEM_ID_NONE:
                    props.append(Condition.characterUses(char_id, item_id))
                if site_id != ELEM_ID_NONE:
                    # GPT can include a location in a uses statement depending on user input.
                    # We break these into two conditions.
                    props.append(Condition.characterAt(char_id, site_id))
                # TODO: consider the uses item on a character - later

        return props
 
    @staticmethod
    def getStrVal(db, prop: ConditionProp) -> str:
        character = None
        item = None
        site = None
        if prop.char_id != ELEM_ID_NONE:
            character = loadCharacter(db, prop.char_id)
        if prop.item_id != ELEM_ID_NONE:
            item = loadItem(db, prop.item_id)
        if prop.site_id != ELEM_ID_NONE:
            site = loadSite(db, prop.site_id)

        if prop.verb == ConditionVerb.AT:
            if character is not None and site is not None:
                return f"{character.getName()} at {site.getName()}"
            if item is not None and site is not None:
                return f"{item.getName()} at {site.getName()}"

        if prop.verb == ConditionVerb.HAS:
            if character is not None and item is not None:
                return f"{character.getName()} has {item.getName()}"

        if prop.verb == ConditionVerb.IS:
            if character is not None and prop.char_status != CharStatus.NONE:
                return f"{character.getName()} is {prop.char_status.value}"

        if prop.verb == ConditionVerb.USES:
            if prop.char_id is not None and character is not None:
                if prop.item_id is not None and item is not None:
                    return f"{character.getName()} uses {item.getName()}"

        return ""

    @staticmethod
    def overlaps(prop1: ConditionProp, prop2: ConditionProp) -> bool:
        """
        Checks if the two properties overlap and could conflict or be equal
        E.G. Check if the two properties specify a location for the same character or item
        """
        # Check item at a location and character has item
        if prop1.item_id != ELEM_ID_NONE and prop1.item_id == prop2.item_id:
            if ((prop1.verb == ConditionVerb.AT or prop1.verb == ConditionVerb.HAS) and
                (prop2.verb == ConditionVerb.AT or prop2.verb == ConditionVerb.HAS)):
                return True

        if prop1.verb != prop2.verb:
            return False

        if prop1.verb == ConditionVerb.AT:
            # Check character at a location
            if prop1.char_id != ELEM_ID_NONE and prop1.char_id == prop2.char_id:
                return True

        elif prop1.verb == ConditionVerb.IS:
            return prop1.char_id == prop2.char_id and prop1.char_status == prop2.char_status

        elif prop1.verb == ConditionVerb.USES:
            return prop1.char_id == prop2.char_id and prop1.item_id == prop2.item_id

        return False

    @staticmethod
    def removeOverlap(properties: list[ConditionProp], prop: ConditionProp):
        """
        Remove a single overlapping property from the list if it exists
        Returns the number of entries removed
        """
        for entry in properties:
            if Condition.overlaps(entry, prop):
                properties.remove(entry)
                return 1
        return 0

    #
    # Methods for start conditions:
    # Note, the implementation produces n-squared behavior. Probably OK, but worth noting.
    #

    @staticmethod
    def getCharStartSite(properties: list[ConditionProp], char_id: ElemID) -> ElemID:
        for entry in properties:
            if entry.char_id == char_id and entry.verb == ConditionVerb.AT:
                return entry.site_id
        return ELEM_ID_NONE


    @staticmethod
    def getItemStartPlace(properties: list[ConditionProp], item_id: ElemID) -> ElemID:
        for entry in properties:
            if entry.item_id == item_id:
                if entry.verb == ConditionVerb.AT:
                    return entry.site_id
                else:
                    return entry.char_id
        return ELEM_ID_NONE

    @staticmethod
    def isCharStatus(properties: list[ConditionProp], char_id: ElemID, char_status: CharStatus) -> bool:
        for entry in properties:
            if entry.verb == ConditionVerb.IS and entry.char_id == char_id and entry.char_status == char_status:
                return True
        return False

class WorldProps(BaseProps):
    plans: typing.Optional[str] = ""
    start_conditions: list[ConditionProp] = []
    end_conditions: list[ConditionProp] = []


class DocSection(pydantic.BaseModel):
    heading: str = ""
    text: str = ""


class DocProps(BaseProps):
    sections: typing.List[DocSection] = []


class CharacterProps(BaseProps):
    personality: str = ""
    appearance: str = ""
    traits: str = ""
    behavior: str = ""
    relationships: str = ""
    backstory: str = ""


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
    effect: ItemEffect = ItemEffect.NONE
    site_id: str = ""


class ItemProps(BaseProps):
    mobile: bool = True
    ability: ItemAbility = ItemAbility()


class SiteProps(BaseProps):
    default_open: bool = True


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

    def __init__(
        self,
        wid: WorldID = WORLD_ID_NONE,
        eid: ElemID = ELEM_ID_NONE,
        element_type: ElementTypeStr = ElementTypeStr.NONE,
    ):
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

    def __init__(self, element_type: ElementType, parent_id: WorldID):
        self.eid = ELEM_ID_NONE
        self.type = element_type
        self.parent_id = parent_id
        self.name = ""
        self.prop_model = BaseProps()
        self.images: list[ElemID] = []  # List of image ids
        self._setProperties({})

    def getID(self) -> ElemID:
        return self.eid

    def hasImage(self) -> bool:
        return len(self.images) > 0

    def getIdName(self) -> IdName:
        return IdName(self.eid, self.name)

    def getElemTag(self) -> ElemTag:
        wid = self.parent_id if self.type != ElementType.WORLD else WorldID(self.eid)
        return ElemTag(wid, self.eid, ElementTypes._typeToName(self.type))

    def _fixProperties(self, properties: dict) -> dict:
        """
        Update any properties that need to change for backwards compatibility
        and migration
        """
        return properties

    def _setProperties(self, properties: dict):
        """
        Set the set of encode properties.
        Override in derived classes
        """
        # Never used
        self.prop_model = BaseProps(**properties)

    def updateProperties(self, properties: dict):
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

    def _getProperties(self) -> dict:
        """
        Return dictonary of encoded properties
        """
        return self.prop_model.model_dump()

    def setPropertiesStr(self, properties: str):
        """
        Take an encoded json string of property values.
        """
        props = self._fixProperties(json.loads(properties))
        self._setProperties(props)

    def getPropertiesStr(self) -> str:
        """
        Return an encoded json string of property values.
        """
        return json.dumps(self._getProperties())

    def getAllProperties(self) -> dict:
        """
        Return a map of properties including id and name,
        exclude internals of type and parent id.
        """
        return {
            CoreProps.PROP_ID: self.eid,
            CoreProps.PROP_NAME: self.name,
            **self._getProperties(),
        }

    def getName(self) -> str:
        return self.name

    def setName(self, name: str):
        self.name = name

    def getDescription(self) -> str:
        if hasattr(self.prop_model, "description"):
            return self.prop_model.description
        return ""

    def setDescription(self, value: str):
        if hasattr(self.prop_model, "description"):
            self.prop_model.description = value

    def getDetails(self) -> str:
        if hasattr(self.prop_model, "details"):
            return self.prop_model.details
        return ""

    def getDetailsHTML(self) -> str:
        return textToHTML(self.getDetails())

    def setDetails(self, value: str):
        if hasattr(self.prop_model, "details"):
            self.prop_model.details = value

    def getInfoText(self) -> list[tuple[int, str]]:
        content = self.getName()
        if len(self.getDescription()) > 0:
            content = content + ": " + self.getDescription()
        if len(self.getDetails()) > 0:
            content = content + "\n" + self.getDetails()
        return [(0, content)]

    def getImages(self) -> list[ElemID]:
        # Return a list of image ids
        return self.images

    def getImageByIndex(self, index: int) -> ElemID | None:
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


def textToHTML(text: str) -> str:
    if text is None:
        return None
    return text.replace("\n\n", "<p>").replace("\n", "<br>")


class World(Element):
    """
    Represents an instance of a World.
    """

    def __init__(self) -> None:
        super().__init__(ElementType.WORLD, WORLD_ID_NONE)
        self.prop_model: WorldProps = WorldProps()

    def getID(self) -> WorldID:
        return WorldID(self.eid)

    def _setProperties(self, properties: dict):
        """
        Set the set of encode properties.
        Override base class
        """
        self.prop_model = WorldProps(**properties)

    def _fixProperties(self, properties: dict) -> dict:
        if properties.get("notes") is not None:
            del properties["notes"]
        return properties
    
    def startConditions(self) -> list[ConditionProp]:
        return self.prop_model.start_conditions

    def endConditions(self) -> list[ConditionProp]:
        return self.prop_model.end_conditions

    def getPlans(self) -> str:
        if self.prop_model.plans is None:
            return ""
        return self.prop_model.plans

    def getPlansHTML(self) -> str:
        return textToHTML(self.getPlans())

    def setPlans(self, value: str):
        self.prop_model.plans = value


class Document(Element):
    """
    Represents a document associated with a world
    """

    def __init__(self, parent_id: WorldID = WORLD_ID_NONE):
        super().__init__(ElementType.DOCUMENT, parent_id)
        self.prop_model: DocProps = DocProps()

    def _setProperties(self, properties: dict):
        """
        Set the set of encode properties.
        Override base class
        """
        self.prop_model = DocProps(**properties)

    def _fixProperties(self, properties: dict) -> dict:
        if properties.get("abstact") is not None:
            del properties["abstract"]
        if properties.get("outline") is not None:
            del properties["outline"]
        return properties

    def getSectionList(self) -> list[str]:
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

    def getInfoText(self) -> list[tuple[int, str]]:
        """
        Return entries of (index, text)
        """
        count = 0
        result = []
        for section in self.prop_model.sections:
            count += 1
            result.append((count, section.heading + " : " + section.text))
        return result


class Character(Element):
    """
    Represents an instance of a Character.
    """

    def __init__(self, parent_id: WorldID = WORLD_ID_NONE):
        super().__init__(ElementType.CHARACTER, parent_id)
        self.prop_model: CharacterProps = CharacterProps()

    def _setProperties(self, properties: dict):
        """
        Set the set of encode properties.
        Override base class
        """
        self.prop_model = CharacterProps(**properties)

    def getPersonality(self) -> str:
        if self.prop_model.personality is None:
            return ""
        return self.prop_model.personality

    def getPersonalityHTML(self) -> str:
        return textToHTML(self.getPersonality())

    def setPersonality(self, value: str):
        self.prop_model.personality = value

    def getAppearance(self) -> str:
        return self.prop_model.appearance

    def setAppearance(self, value: str) -> None:
        self.prop_model.appearance = value

    def getTraits(self) -> str:
        return self.prop_model.traits

    def setTraits(self, value: str) -> None:
        self.prop_model.traits = value

    def getBehavior(self) -> str:
        return self.prop_model.behavior

    def setBehavior(self, value: str) -> None:
        self.prop_model.behavior = value

    def getRelationships(self) -> str:
        return self.prop_model.relationships

    def setRelationships(self, value: str) -> None:
        self.prop_model.relationships = value

    def getBackstory(self) -> str:
        return self.prop_model.backstory

    def setBackstory(self, value: str) -> None:
        self.prop_model.backstory = value

    def getProfile(self) -> str:
        content = list()
        content.append("Name: " + self.getName())
        content.append("[Description]")
        content.append(self.getDescription())
        if len(self.getDetails()) > 0:
            content.append("[Details]")
            content.append(self.getDetails())
        if len(self.getAppearance()) > 0:
            content.append("[Appearance]")
            content.append(self.getAppearance())
        if len(self.getTraits()) > 0:
            content.append("[Traits]")
            content.append(self.getTraits())
        if len(self.getBehavior()) > 0:
            content.append("[Behavior]")
            content.append(self.getBehavior())
        if len(self.getRelationships()) > 0:
            content.append("[Relationships]")
            content.append(self.getRelationships())
        if len(self.getBackstory()) > 0:
            content.append("[Backstory]")
            content.append(self.getBackstory())
        return "\n".join(content)

    def getInfoText(self) -> list[tuple[int, str]]:
        return [(0, self.getProfile())]


class Site(Element):
    """
    Represents an instance of a Site
    """

    def __init__(self, parent_id: WorldID = WORLD_ID_NONE):
        super().__init__(ElementType.SITE, parent_id)
        self.prop_model: SiteProps = SiteProps()

    def _fixProperties(self, properties: dict) -> dict:
        if properties.get("locked") is not None:
            properties["default_open"] = not properties["locked"]
            del properties["locked"]
        return properties

    def _setProperties(self, properties: dict):
        """
        Set the set of encode properties.
        Override base class
        """
        self.prop_model = SiteProps(**properties)

    def getDefaultOpen(self) -> bool:
        return self.prop_model.default_open

    def setDefaultOpen(self, value: bool):
        self.prop_model.default_open = value


class Item(Element):
    """
    Represents an instance of an Item
    """

    def __init__(self, parent_id: WorldID = WORLD_ID_NONE):
        super().__init__(ElementType.ITEM, parent_id)
        self.prop_model: ItemProps = ItemProps()

    def _fixProperties(self, properties: dict) -> dict:
        if properties.get("ability") is not None:
            if properties["ability"].get("effect") is not None:
                if properties["ability"]["effect"] == "unlock":
                    properties["ability"]["effect"] = "open"
                if properties["ability"]["effect"] == "":
                    properties["ability"]["effect"] = "none"
        return properties

    def _setProperties(self, properties: dict):
        """
        Set the set of encode properties.
        Override base class
        """
        self.prop_model = ItemProps(**properties)

    def getIsMobile(self) -> bool:
        return self.prop_model.mobile

    def setIsMobile(self, value: bool):
        self.prop_model.mobile = value

    def getAbility(self) -> ItemAbility:
        return self.prop_model.ability

    def setAbility(self, ability: ItemAbility):
        self.prop_model.ability = ability

    def getInfoText(self) -> list[tuple[int, str]]:
        return [(0, self.getProfile())]

    def getProfile(self) -> str:
        # Append item ability to the info text
        content = self.getName()
        if self.getIsMobile():
            content += "\nIs mobile\n"
        else:
            content += "\nIs not mobile\n"
        content += "Key Function: "
        if self.getAbility().effect == ItemEffect.OPEN:
            content += "Open a site\n"
        else:
            content += self.getAbility().effect + "\n"

        if self.getDescription() is not None:
            content = content + self.getDescription()
        if self.getDetails() is not None:
            content = content + "\n" + self.getDetails()
        return content


class ElementStore:
    @staticmethod
    def loadElement(db, eid: ElemID, element: Element):
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
    def findElement(db, pid: WorldID, name: str, element: Element):
        """
        Return an element id
        """
        name = '%' + name + '%'
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
    def updateElement(db, element: Element):
        db.execute(
            "UPDATE elements SET  name = ?, properties = ? "
            + "WHERE id = ? and type = ?",
            (element.name, element.getPropertiesStr(), element.eid, element.type),
        )
        db.commit()

    @staticmethod
    def createElement(db, element: Element) -> ElemID:
        """
        Return an element insance
        """
        element.eid = ElemID("id%s" % os.urandom(4).hex())
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
        return element.eid

    @staticmethod
    def getElements(db, element_type: ElementType, parent_id: WorldID) -> list[IdName]:
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
    def hideElement(db, element: Element, wid: WorldID, name: str):
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
    def recoverElements(db, element_type: ElementType, parent_id: WorldID):
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

    def __init__(self, iid: ElemID = ELEM_ID_NONE):
        self.iid = iid
        self.filename: str = ""
        self.prompt: str = ""
        self.parent_id: ElemID = ELEM_ID_NONE

    def getID(self) -> ElemID:
        return self.iid

    def setPrompt(self, prompt: str):
        self.prompt = prompt

    def setParentId(self, parent_id: ElemID):
        self.parent_id = parent_id

    def getFilename(self) -> str:
        if len(self.filename) == 0:
            self.filename = os.urandom(12).hex() + ".png"
        return self.filename

    def getThumbName(self) -> str:
        filename = self.getFilename()
        return filename[0:-4] + ".thmb" + filename[-4:]


def createImage(db, image: Image):
    image.iid = ElemID("id%s" % os.urandom(4).hex())
    db.execute(
        "INSERT INTO images (id, parent_id, prompt, filename) " + "VALUES (?, ?, ?, ?)",
        (image.iid, image.parent_id, image.prompt, image.filename),
    )
    db.commit()
    return image


def getImageFromIndex(db, parent_id: ElemID, index: int) -> Image | None:
    # Convert index ordinal (0, 1, 2, ...) to an image id
    # TODO: Note this is probably broken and we need an ordering.
    images = listImages(db, parent_id)
    if len(images) > index:
        return images[index]["id"]
    return None


def hideImage(db, iid: ElemID):
    db.execute("UPDATE images SET is_hidden = TRUE WHERE id = ?", (iid,))
    db.commit()


def recoverImages(db, parent_id: ElemID):
    c = db.cursor()
    c.execute(
        "UPDATE images SET is_hidden = FALSE WHERE parent_id = ? "
        + "AND is_hidden = TRUE",
        (parent_id,),
    )
    db.commit()
    return c.rowcount


def getImageFile(db, data_dir: str, iid: ElemID) -> io.BufferedIOBase | None:
    q = db.execute("SELECT filename FROM images WHERE id = ?", (iid,))
    r = q.fetchone()
    if r is not None:
        filename = r[0]
        f = open(os.path.join(data_dir, filename), "rb")
        return f
    return None


def getImage(db, iid: ElemID) -> Image | None:
    q = db.execute(
        "SELECT parent_id, prompt, filename FROM images WHERE id = ?", (iid,)
    )
    r = q.fetchone()
    if r is not None:
        image = Image(iid)
        image.parent_id = r[0]
        image.prompt = r[1]
        image.filename = r[2]
        return image
    return None


def listImages(db, parent_id: ElemID, include_hidden: bool = False) -> list[dict]:
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


def getImages(db, parent_id: ElemID = WORLD_ID_NONE) -> list[Image]:
    """
    Return a list of image elements.
    If parent_id is None, return all images.
    Otherwise, return images for specified element.
    """
    result = []
    if parent_id is not None and parent_id != WORLD_ID_NONE:
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


def getElemTag(db, eid: ElemID) -> ElemTag | None:
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


def idNameToElemTag(db, idName: IdName) -> ElemTag | None:
    if idName is None:
        return None
    return getElemTag(db, idName.getID())


def listWorlds(db) -> list[IdName]:
    """
    Return a list of worlds.
    """
    return ElementStore.getElements(db, ElementType.WORLD, WORLD_ID_NONE)


def loadWorld(db, eid: ElemID) -> Optional[World]:
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
    world.eid = ElementStore.createElement(db, world)
    return world


def updateWorld(db, world: World):
    ElementStore.updateElement(db, world)


def createDocument(db, document: Document) -> Document:
    """
    Return a document instance
    """
    document.eid = ElementStore.createElement(db, document)
    return document


def listDocuments(db, world_id: WorldID) -> list[IdName]:
    return ElementStore.getElements(db, ElementType.DOCUMENT, world_id)


def loadDocument(db, eid) -> Optional[Document]:
    return ElementStore.loadElement(db, eid, Document())


def findDocument(db, wid: WorldID, name: str) -> Optional[Document]:
    return ElementStore.findElement(db, wid, name, Document())


def updateDocument(db, document: Document):
    ElementStore.updateElement(db, document)


def listCharacters(db, world_id: WorldID) -> list[IdName]:
    """
    Return a list of characters.
    """
    return ElementStore.getElements(db, ElementType.CHARACTER, world_id)


def loadCharacter(db, eid: ElemID) -> Optional[Character]:
    """
    Return a character instance
    """
    if eid == PLAYER_ID:
        # Special handling for a player record. Unsure if this is a good approach
        char = Character()
        char.name = "Player"
        char.eid = PLAYER_ID
        return char

    return ElementStore.loadElement(db, eid, Character())


def findCharacter(db, wid: WorldID, name: str) -> Optional[Character]:
    """
    Return a character instance by name
    """
    return ElementStore.findElement(db, wid, name, Character())


def createCharacter(db, character: Character) -> Character:
    """
    Return a character instance
    """
    character.eid = ElementStore.createElement(db, character)
    return character


def updateCharacter(db, character: Character):
    ElementStore.updateElement(db, character)


def hideCharacter(db, wid: WorldID, name: str) -> int:
    count = ElementStore.hideElement(db, Character(), wid, name)
    return count == 1


def recoverCharacters(db, world_id: WorldID) -> int:
    return ElementStore.recoverElements(db, ElementType.CHARACTER, world_id)


def listSites(db, world_id: WorldID) -> list[IdName]:
    """
    Return a list of sites.
    """
    return ElementStore.getElements(db, ElementType.SITE, world_id)


def loadSite(db, eid: ElemID) -> Optional[Site]:
    """
    Return a site instance
    """
    return ElementStore.loadElement(db, eid, Site())


def findSite(db, pid: WorldID, name: str) -> Optional[Site]:
    """
    Return a site instance by name
    """
    return ElementStore.findElement(db, pid, name, Site())


def createSite(db, site: Site) -> Site:
    """
    Return a site instance
    """
    site.eid = ElementStore.createElement(db, site)
    return site


def updateSite(db, site: Site):
    ElementStore.updateElement(db, site)


def hideSite(db, wid: WorldID, name: str) -> int:
    count = ElementStore.hideElement(db, Site(), wid, name)
    return count == 1


def recoverSites(db, world_id: WorldID) -> int:
    return ElementStore.recoverElements(db, ElementType.SITE, world_id)


def listItems(db, world_id: WorldID) -> list[IdName]:
    """
    Return a list of sites.
    """
    return ElementStore.getElements(db, ElementType.ITEM, world_id)


def loadItem(db, eid: ElemID) -> Optional[Item]:
    """
    Return an item instance
    """
    return ElementStore.loadElement(db, eid, Item())


def findItem(db, pid: WorldID, name: str) -> Optional[Item]:
    """
    Return an item instance by name
    """
    return ElementStore.findElement(db, pid, name, Item())


def createItem(db, item: Item) -> Item:
    """
    Return an Item instance
    """
    item.eid = ElementStore.createElement(db, item)
    return item


def updateItem(db, item: Item):

    ElementStore.updateElement(db, item)


def hideItem(db, wid: WorldID, name: str) -> int:
    count = ElementStore.hideElement(db, Item(), wid, name)
    return count == 1


def recoverItems(db, world_id: WorldID) -> int:
    return ElementStore.recoverElements(db, ElementType.ITEM, world_id)

def getItemAbilityDescription(db, item: Item) -> str:
    ability = item.getAbility().effect
    if ability == ItemEffect.OPEN:
        site = loadSite(db, ElemID(item.getAbility().site_id))
        if site is not None:
            return ability + " " + site.getName()
    return ability



def deleteImage(db, data_dir: str, image_id: ElemID):
    image = getImage(db, image_id)
    if image is None:
        return

    db.execute("DELETE FROM images WHERE id = ?", (image_id,))
    db.commit()
    logging.info("remove image: %s", image_id)
    path = os.path.join(data_dir, image.filename)
    try:
        os.unlink(path)
        logging.info("delete file: %s", path)
    except FileNotFoundError:
        pass


def deleteCharacter(db, data_dir: str, eid: ElemID):
    character = loadCharacter(db, eid)
    if character is None:
        return

    logging.info("delete character: [%s] %s", character.eid, character.getName())
    images = listImages(db, eid, include_hidden=True)

    for image in images:
        deleteImage(db, data_dir, image["id"])

    db.execute(
        "DELETE FROM elements WHERE id = ? AND type = ?", (eid, ElementType.CHARACTER)
    )
    db.commit()


def deleteWorld(db, data_dir: str, world_id: WorldID):
    world = loadWorld(db, world_id)
    if world is None:
        return

    logging.info("delete world: [%s] %s", world.eid, world.getName())
    characters = listCharacters(db, world_id)
    for entry in characters:
        deleteCharacter(db, data_dir, entry.getID())
    # TODO: Delete items, sites, docs

    images = listImages(db, world.eid, include_hidden=True)
    for image in images:
        deleteImage(db, data_dir, image["id"])

    db.execute(
        "DELETE FROM elements WHERE id = ? AND type = ?", (world.eid, ElementType.WORLD)
    )
    db.commit()


def getAdjacentElements(id_name: IdName, id_name_list: list[IdName]):
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
