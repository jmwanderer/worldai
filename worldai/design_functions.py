import json
import logging
import os

import openai
import requests
from PIL import Image

from . import chat_functions, element_info, elements

IMAGE_DIRECTORY = "/tmp"
TESTING = False

STATE_WORLDS = "State_Worlds"
STATE_WORLD = "State_World"
STATE_WORLD_EDIT = "State_World_Edit"
STATE_DOCUMENTS = "State_Documents"
STATE_CHARACTERS = "State_Characters"
STATE_ITEMS = "State_Items"
STATE_SITES = "State_Sites"


def elemTypeToState(element_type):
    if element_type == elements.ElementTypes.WorldType():
        return STATE_WORLD
    if element_type == elements.ElementTypes.DocumentType():
        return STATE_DOCUMENTS
    if element_type == elements.ElementTypes.CharacterType():
        return STATE_CHARACTERS
    if element_type == elements.ElementTypes.ItemType():
        return STATE_ITEMS
    if element_type == elements.ElementTypes.SiteType():
        return STATE_SITES
    return STATE_WORLDS


states = {
    STATE_WORLDS: ["ListWorlds", "ShowWorld", "CreateWorld"],
    STATE_WORLD: [
        "ReadPlans",
        "ShowWorld",
        "ShowCharacter",
        "ShowItem",
        "ShowSite",
        "ChangeState",
        "EditWorld",
        "GetStartConditions",
    ],
    STATE_WORLD_EDIT: [
        "UpdateWorld",
        "ShowWorld",
        "ReadPlans",
        "UpdatePlans",
        "CreateWorldImage",
        "ChangeState",
        "RemoveWorldImage",
        "RecoverWorldImages",
        "SetStartCondition",
        "GetStartConditions",
    ],
    STATE_DOCUMENTS: [
        "ListDocuments",
        "CreateDocument",
        "UpdateDocument",
        "AddDocumentSection",
        "UpdateDocumentSection",
        "ShowDocument",
        "ReadDocumentSection",
        "ChangeState",
    ],
    STATE_CHARACTERS: [
        "ListCharacters",
        "ShowCharacter",
        "CreateCharacter",
        "UpdateCharacter",
        "ReadPlans",
        "CreateCharacterImage",
        "ChangeState",
        "RemoveCharacter",
        "RecoverCharacters",
        "RemoveImage",
        "RecoverImages",
    ],
    STATE_ITEMS: [
        "ListItems",
        "ShowItem",
        "CreateItem",
        "UpdateItem",
        "ReadPlans",
        "CreateItemImage",
        "ChangeState",
        "RemoveItem",
        "RecoverItems",
        "RemoveImage",
        "RecoverImages",
    ],
    STATE_SITES: [
        "ListSites",
        "ShowSite",
        "CreateSite",
        "UpdateSite",
        "ReadPlans",
        "CreateSiteImage",
        "ChangeState",
        "RemoveSite",
        "RecoverSites",
        "RemoveImage",
        "RecoverImages",
    ],
}


GLOBAL_INSTRUCTIONS = """
You are a co-designer of fictional worlds which will be the setting for adventure stories.
You develop ideas, backstories, and content for these worlds, including
new unique fictional characters, key sites in the world, and significant items that appear in the stories.
You can format in markdown.
A good story has protagonists and antagonists, hnd characters with flaws, strengths and weaknesses. 

We design the world with a name and a high level description and create background details

Save high level ideas on characters, items, and sites in the world plan.

We can be in one of the following states:
- State_Worlds: We can list and show existing worlds and create new worlds
- State_World: We view a world description, details, and Plans.
- State_World_Edit: We change a world description, details, plans, and starting conditions.
- State_Documents: We view and edit background documents for the world.
- State_Characters: We can view characters and create new characters and change the description and details of a character.
- State_Items: We can view items and create new items and change the description and details of an item.
- State_Sites: We can view sites and create new sites and change the description and details of a site.

The current state is "{current_state}"

Suggest good ideas for descriptions and details for the worlds, characters, sites, and items.
Suggest next steps to the user in designing a complete world.
"""


instructions = {
    STATE_WORLDS: """
You can create a new world or resume work on an existing one by showing it.
To modify an existing world, ChangeState to State_World.
To get a list of worlds, call ListWorlds
Get a list of worlds before showing a world or creating a new one
""",
    STATE_WORLD: """
We are working on the world "{current_world_name}": {current_world_description}

A world has plans that list the planned main characters, key sites, and special items. Read plans for the world by calling ReadPlans  

Modify world attributes by calling EditWorld

To view, create, or update characters, change state to State_Characters.
To view, create, or update items, change state to State_Items.
To view, create, or update sites, change state to State_Sites.  

  """,
    STATE_WORLD_EDIT: """
We are working on the world "{current_world_name}": {current_world_description}
  
When building a world, we generally go through the following steps:
- Set the name and a short high level description
- Develop planning notes with the main points of the design
- Develop details for the world describing the key elements
- Define the main characters that are the key actors in our world story
- Define the key sites in the world wher our story takes place
- Define the important items that could be important in the story
- Develop background and detailed documents for the world

Build prompts to create images using information from the description, and details in the prompt.

Save changes to the world by calling UpdateWorld

To view information about characters, items, or sites, change the state to State_World
  """,
    STATE_DOCUMENTS: """
We are working on world "{current_world_name}": {current_world_description}
{element}

We create and edit background documents for the world, creating an abstract, outline and
document contents by calling AddDocumentSection. Change the abstract, outline, and contents
by calling UpdateDocumentSection.

Good documents talk about the history of the world, and give a background of the people and events
that led to they way things are today. Documents may explain the political situation, major conflicts,
heros and antagonists.

To work on something other than documents, call ChangeState
""",
    STATE_CHARACTERS: """
We are working on world "{current_world_name}": {current_world_description}
{element}

Worlds have characters which are actors in the world. 
Characters have a description of appearance, relationships, abilities, weaknesses, motivations and a backstory.
Characters have a personality that include how they talk, act, and think. Does the person tend towards good or evil?
Selfishnes or selflessness?  Law abiding or chaotic?
You can create characters and change information about the characters.

You can update the name, description, details, and personality of the character.
You save changes to a character by calling UpdateCharacter.  

Use information in the world details to guide character creation and design.

When creating images for the character using CreateCharacterImage, make a long prompt using the character description, details, 
and personality.

Save detailed information about the character in character details.

To work on information about the world call ChangeState
To work on items or sites, call ChangeState
""",
    STATE_ITEMS: """
We are working on world "{current_world_name}": {current_world_description}
{element}

Worlds have items which exist in the world and have special significance.  You can create items and change information about the items.
Items may have an ability, such as 'hurt', 'heal', 'invisibility'.

You can update the name, description, details, mobility, and ability of an item.
You save changes to an item by calling UpdateItem.  

Use information in the world details to guide item creation and design.

When creating images for the item with CreateItemImage, make a long prompt using the item description and details.

Save detailed information about the item in item details.

To view or change information about the world call ChangeState
To view or work characters or sites, call ChangeState
""",
    STATE_SITES: """
We are working on world "{current_world_name}": {current_world_description}
{element}

Worlds have sites which are significant locations. Cities, buildings, and special areas may all be sites. You can create sites and change information about the sites.

You can update the name, description, and details of a site.
You save changes to a site by calling UpdateSite.  

Use information in the world details to guide site creation and design.

When creating images for the site with CreateSiteImage, make a long prompt using the site description and details.

Save detailed information about the site in site details.

To work on information about the world call ChangeState
To work on characters or items, call ChangeState
""",
}


def checkDuplication(name, element_list):
    """
    Check for any collisions between name and existing list
    element_list: list returned from getElements

    Return None if no conflict
    Return an id if a conflict

    """
    # Check if name is a substring of any existing name
    name = name.lower()
    for element in element_list:
        if name in element.getName().lower():
            return element.getID()

    # Check if any existing name is a substring of the new name
    for element in element_list:
        if element.getName().lower() in name:
            return element.getID()

    return None

class ChatCall:
    def __init__(self):
        self.user_msg = None
        self.tool_call = None
        self.system_message = None

    def getProps(self):
        props = {}
        if self.user_msg is not None:
            props["user_msg"] = self.user_msg
        if self.tool_call is not None:
            props["tool_call"] = self.tool_call
        if self.system_message is not None:
            props["system_message"] = self.system_message
        return props

    def setProps(self, props):
        if props.get("user_msg") is not None:
            self.user_msg = props["user_msg"]
        if props.get("tool_call") is not None:
            self.tool_call = props["tool_call"]
        if props.get("system_message") is not None:
            self.system_message = props["system_message"]

    def toStr(self):
        lines = []
        if self.user_msg is not None:
            lines.append("user_msg: " + self.user_msg)
        if self.tool_call is not None:
            lines.append("tool_call: " + self.tool_call)
        if self.system_message is not None:
            lines.append("system_message: " + self.system_message) 
        if len(lines) == 0:
            return "empty"
        return ", ".join(lines)


class DesignFunctions(chat_functions.BaseChatFunctions):

    def __init__(self):
        chat_functions.BaseChatFunctions.__init__(self)
        self.current_state = STATE_WORLDS

        # Tracks current world, current element
        self.current_view = elements.ElemTag()

        # An ElemTag that describes a view we need to change into.
        # The none elem tag means that there is no change for the view.
        # This happens when the user changes the view in the UI.
        # We need to sync the GPT to the new view
        # TODO: remove this
        self.next_view = elements.ElemTag()
        self.pending_chat_calls : list[ChatCall] = []
        self.message_done: bool = True

    # Class variables for puplic properties for each type
    WORLD_PROPS = ["name", "description", "details"]
    CHAR_PROPS = ["name", "description", "details", "personality"]
    ITEM_PROPS = ["name", "description", "details", "mobile", "ability"]
    SITE_PROPS = ["name", "description", "details", "default_open"]

    def getProperties(self):
        properties = super().getProperties()
        properties["current_state"] = self.current_state
        properties["current_view"] = self.current_view.json()
        properties["next_view"] = self.next_view.json()
        pending_calls = []
        for chat_call in self.pending_chat_calls:
            pending_calls.append(chat_call.getProps())
        properties["pending_calls"] = pending_calls
        properties["message_done"] = self.message_done
        return properties

    def setProperties(self, properties):
        super().setProperties(properties)
        self.current_state = properties["current_state"]
        self.current_view = elements.ElemTag.JsonTag(properties["current_view"])
        self.next_view = elements.ElemTag.JsonTag(properties["next_view"])
        if properties.get("message_done") is not None:
            self.message_done = properties["message_done"]
        if properties.get("pending_calls") is not None:
            for entry in properties["pending_calls"]:
                chat_call = ChatCall()
                chat_call.setProps(entry)
                self.pending_chat_calls.append(chat_call)

    def getCurrentWorldID(self):
        # May return None
        return self.current_view.getWorldID()

    def getCurrentWorldName(self, db):
        # May return None
        world = self.getCurrentWorld(db)
        if world is not None:
            return world.getName()
        return None

    def getCurrentWorldDescription(self, db):
        # May return None
        world = self.getCurrentWorld(db)
        if world is not None:
            return world.getDescription()
        return None

    def getCurrentWorld(self, db):
        # May return None
        if self.current_view.getWorldID() is None:
            return None
        return elements.loadWorld(db, self.getCurrentWorldID())

    def getCurrentViewType(self):
        return self.current_view.getType()

    def getCurrentElementName(self, db):
        if self.getCurrentViewType() == elements.ElementTypes.CharacterType():
            character = elements.loadCharacter(db, self.current_view.getID())
            return character.getName()

        if self.getCurrentViewType() == elements.ElementTypes.SiteType():
            site = elements.loadSite(db, self.current_view.getID())
            return site.getName()

        if self.getCurrentViewType() == elements.ElementTypes.ItemType():
            item = elements.loadItem(db, self.current_view.getID())
            return item.getName()

        if self.getCurrentViewType() == elements.ElementTypes.DocumentType():
            doc = elements.loadDocument(db, self.current_view.getID())
            return doc.getName()
        return ""

    def clearCurrentView(self):
        self.current_view = elements.ElemTag()

    def get_instructions(self, db):
        global_instructions = GLOBAL_INSTRUCTIONS.format(
            current_state=self.current_state
        )
        return global_instructions + "\n" + self.get_state_instructions(db)

    def get_state_instructions(self, db):
        element = ""
        if self.getCurrentViewType() == elements.ElementTypes.CharacterType():
            element = (
                f"We are looking at the character '{self.getCurrentElementName(db)}'"
            )
        elif self.getCurrentViewType() == elements.ElementTypes.ItemType():
            element = f"We are looking at the item '{self.getCurrentElementName(db)}'"
        elif self.getCurrentViewType() == elements.ElementTypes.SiteType():
            element = f"We are looking at the site '{self.getCurrentElementName(db)}'"
        elif self.getCurrentViewType() == elements.ElementTypes.DocumentType():
            element = (
                f"We are looking at the document '{self.getCurrentElementName(db)}'"
            )

        value = instructions[self.current_state].format(
            current_world_name=self.getCurrentWorldName(db),
            current_world_description=self.getCurrentWorldDescription(db),
            element=element,
        )

        if self.current_state != STATE_WORLDS:
            value = value + "\n" + self.getWorldPop(db, self.getCurrentWorldID())
        return value

    def getWorldPop(self, db, world_id):
        population = []
        population.append("Existing Characters:\n")
        for character in elements.listCharacters(db, world_id):
            population.append(f"- {character.getName()}")
        population.append("")

        population.append("Existing Items:\n")
        for item in elements.listItems(db, world_id):
            population.append(f"- {item.getName()}")
        population.append("")

        population.append("Existing Sites:\n")
        for site in elements.listSites(db, world_id):
            population.append(f"- {site.getName()}")

        return "\n".join(population)

    def get_available_tools(self):
        return self.get_available_tools_for_state(self.current_state)

    def get_available_tools_for_state(self, state):
        functions = {}
        for function in all_functions:
            functions[function["name"]] = function

        result = []
        for name in states[state]:
            tool = {"type": "function", "function": functions[name]}
            result.append(tool)
        return result

    def track_tokens(self, db, prompt, complete, total):
        world_id = self.getCurrentWorldID()
        if world_id is None:
            world_id = 0
        chat_functions.track_tokens(db, world_id, prompt, complete, total)

    def get_view(self):
        return self.current_view.json()

    def set_next_view(self, next_view):
        """
        Set the target view.
        If same as current, this is a NO-OP
        """
        next_view = elements.ElemTag.JsonTag(next_view)
        logging.info("next view -- %s", next_view.jsonStr())
        logging.info("current view -- %s", self.current_view.jsonStr())
        self.next_view = next_view

    def execute_function_call(self, db, function_name, arguments):
        """
        Dispatch function for function_name
        Takes:
          function_name - string
          arguments - dict build from json.loads
        Returns
          dict ready for json.dumps
        """
        # Default response value
        result = '{ "error": "' + f"no such function: {function_name}" + '" }'

        if function_name not in states[self.current_state]:
            result = self.funcError(
                f"No available function {function_name}. " + "Perhaps call ChangeState"
            )

        elif function_name == "EditWorld":
            self.current_state = STATE_WORLD_EDIT
            result = self.funcStatus("edit enabled")

        elif function_name == "ChangeState":
            result = self.FuncChangeState(db, arguments)

        elif function_name == "CreateWorld":
            result = self.FuncCreateWorld(db, arguments)

        elif function_name == "ListWorlds":
            result = [{"name": entry.getName()} for entry in elements.listWorlds(db)]

        elif function_name == "UpdateWorld":
            result = self.FuncUpdateWorld(db, arguments)

        elif function_name == "ShowWorld":
            result = self.FuncReadWorld(db, arguments)

        elif function_name == "ReadPlans":
            result = self.FuncReadPlanningNotes(db, arguments)

        elif function_name == "UpdatePlans":
            result = self.FuncUpdatePlanningNotes(db, arguments)

        elif function_name == "SetStartCondition":
            result = self.FuncSetStartCondition(db, arguments)

        elif function_name == "GetStartConditions":
            result = self.FuncGetStartConditions(db)

        elif function_name == "ListDocuments":
            result = self.FuncListDocuments(db)

        elif function_name == "CreateDocument":
            result = self.FuncCreateDocument(db, arguments)

        elif function_name == "UpdateDocument":
            result = self.FuncUpdateDocument(db, arguments)

        elif function_name == "ShowDocument":
            result = self.FuncShowDocument(db, arguments)

        elif function_name == "ReadDocumentSection":
            result = self.FuncReadDocumentSection(db, arguments)

        elif function_name == "AddDocumentSection":
            result = self.FuncAddDocumentSection(db, arguments)

        elif function_name == "UpdateDocumentSection":
            result = self.FuncUpdateDocumentSection(db, arguments)

        elif function_name == "ListCharacters":
            result = [
                {"name": entry.getName()}
                for entry in elements.listCharacters(db, self.getCurrentWorldID())
            ]

        elif function_name == "ShowCharacter":
            result = self.FuncReadCharacter(db, arguments)

        elif function_name == "CreateCharacter":
            result = self.FuncCreateCharacter(db, arguments)

        elif function_name == "UpdateCharacter":
            result = self.FuncUpdateCharacter(db, arguments)

        elif function_name == "ListItems":
            result = [
                {"name": entry.getName()}
                for entry in elements.listItems(db, self.getCurrentWorldID())
            ]

        elif function_name == "ShowItem":
            result = self.FuncReadItem(db, arguments)

        elif function_name == "CreateItem":
            result = self.FuncCreateItem(db, arguments)

        elif function_name == "UpdateItem":
            result = self.FuncUpdateItem(db, arguments)

        elif function_name == "ListSites":
            result = [
                {"name": entry.getName()}
                for entry in elements.listSites(db, self.getCurrentWorldID())
            ]

        elif function_name == "ShowSite":
            result = self.FuncReadSite(db, arguments)

        elif function_name == "CreateSite":
            result = self.FuncCreateSite(db, arguments)

        elif function_name == "UpdateSite":
            result = self.FuncUpdateSite(db, arguments)

        elif function_name in [
            "CreateWorldImage",
            "CreateCharacterImage",
            "CreateItemImage",
            "CreateSiteImage",
        ]:
            result = self.FuncCreateImage(db, arguments)

        elif function_name in ["RemoveImage", "RemoveWorldImage"]:
            result = self.FuncRemoveImage(db, arguments)

        elif function_name in ["RecoverImages", "RecoverWorldImages"]:
            result = self.FuncRecoverImages(db, arguments)

        elif function_name in ["RemoveSite", "RemoveCharacter", "RemoveItem"]:
            result = self.FuncRemoveElement(db, arguments)

        elif function_name in ["RecoverSites", "RecoverItems", "RecoverCharacters"]:
            result = self.FuncRecoverElements(db, arguments)

        if self.current_state == STATE_WORLDS:
            self.current_view = elements.ElemTag()
        elif self.current_state == STATE_WORLD:
            self.current_view = elements.ElemTag.WorldTag(self.getCurrentWorldID())
        return result

    def FuncChangeState(self, db, arguments):
        if arguments.get("state") is None:
            return self.funcError("Missing argument 'name'")
        state = arguments["state"]
        if states.get(state) is None:
            return self.funcError(f"unknown state: {state}")

        # Check is state is legal - TODO: more states here?
        if state in [STATE_WORLD, STATE_CHARACTERS] and self.current_view.noElement():
            return self.funcError(f"Must read or create a world for {state}")
        self.current_state = state

        return self.funcStatus(f"state changed: {state}")

    def FuncCreateWorld(self, db, arguments):
        world = elements.World()
        if arguments.get("name") is None:
            return self.funcError("Missing argument 'name'")
        world.setName(arguments["name"])
        world.updateProperties(arguments)

        # Check for duplicates
        worlds = elements.listWorlds(db)
        name = checkDuplication(world.getName(), worlds)
        if name is not None:
            return self.funcError(f"Similar name already exists: {name}")

        world = elements.createWorld(db, world)
        self.current_state = STATE_WORLD
        self.current_view = world.getElemTag()
        self.modified = True
        status = self.funcStatus("created world")
        status["name"] = world.getName()
        element_info.UpdateElementInfo(db, world)
        return status

    def FuncUpdateWorld(self, db, arguments):
        world = elements.loadWorld(db, self.getCurrentWorldID())
        if world is None:
            return self.funcError(f"World not found {self.getCurrentWorldID()}")
        world.updateProperties(arguments)
        # TODO: check name collision
        elements.updateWorld(db, world)
        self.modified = True
        status = self.funcStatus("updated world")
        status["name"] = world.getName()
        element_info.UpdateElementInfo(db, world)
        return status

    def FuncReadWorld(self, db, arguments):
        if arguments.get("name") is None:
            return self.funcError("Missing argument 'name'")
        name = arguments["name"]
        world = elements.findWorld(db, name)
        if world is None:
            return self.funcError(f"no world '{name}', perahps call ListWorlds")

        content = {
            key: world.getAllProperties()[key] for key in DesignFunctions.WORLD_PROPS
        }
        content["has_image"] = world.hasImage()

        # Add information on the existing elements of the world.
        content["has_plans"] = len(world.getPlans()) > 0

        # Side affect, change state
        self.current_state = STATE_WORLD
        self.current_view = world.getElemTag()
        return content

    def FuncReadPlanningNotes(self, db, arguments):
        world = elements.loadWorld(db, self.getCurrentWorldID())
        if world is None:
            return self.funcError(f"World not found {self.getCurrentWorldID()}")
        content = {"plans": world.getPlans()}
        return content

    def FuncUpdatePlanningNotes(self, db, arguments):
        world = elements.loadWorld(db, self.getCurrentWorldID())
        if world is None:
            return self.funcError(f"World not found {self.getCurrentWorldID()}")
        world.setPlans(arguments["plans"])
        elements.updateWorld(db, world)
        self.modified = True
        status = self.funcStatus("updated world plans")
        status["name"] = world.getName()
        return status

    def FuncGetStartConditions(self, db):
        world_id = self.getCurrentWorldID()
        world = elements.loadWorld(db, world_id)
        result = []
        for prop in world.startConditions():
            result.append(elements.Condition.getStrVal(db, prop))
        return result
 
    def FuncSetStartCondition(self, db, arguments):
        world_id = self.getCurrentWorldID()
        world = elements.loadWorld(db, world_id)
        if world is None:
            return self.funcError(f"World not found {world_id}")
        verb = arguments.get("verb")
        if verb is None:
            return self.funcError(f"Must have a verb: is, has, at, ...")

        item_id = elements.ELEM_ID_NONE
        char_id = elements.ELEM_ID_NONE
        site_id = elements.ELEM_ID_NONE

        item_name = arguments.get("item")
        if item_name is not None:
            item = elements.findItem(db, world_id, item_name)
            if item is not None:
                item_id = item.getID()
            else:
                return self.funcError(f"Unknown item {item_name}")

        character_name = arguments.get("character")
        if character_name is not None:
            character = elements.findCharacter(db, world_id, character_name)
            if character is not None:
                char_id = character.getID()
            else:
                return self.funcError(f"Unknown character {character_name}")

        site_name = arguments.get("site")
        if site_name is not None:
            site = elements.findSite(db, world_id, site_name)
            if site is not None:
                site_id = site.getID()
            else:
                return self.funcError(f"Unknown site {site_name}")

        prop = None
        if verb == elements.ConditionVerb.AT:
            if char_id != elements.ELEM_ID_NONE and site_id != elements.ELEM_ID_NONE:
                prop = elements.Condition.characterAt(char_id, site_id)
            elif item_id != elements.ELEM_ID_NONE and site_id != elements.ELEM_ID_NONE:
                prop = elements.Condition.itemAt(item_id, site_id)
        elif verb == elements.ConditionVerb.HAS:
            if char_id != elements.ELEM_ID_NONE and item_id != elements.ELEM_ID_NONE:
                prop = elements.Condition.characterHas(char_id, item_id)    
        
        if prop is None:
            return self.funcError("Did not understand the condition")

        elements.Condition.removeOverlap(world.startConditions(), prop)
        world.startConditions().append(prop)
        elements.updateWorld(db, world)
        return self.funcStatus("Condition added")

 

    def FuncListDocuments(self, db):
        result = []
        entries = elements.listDocuments(db, self.getCurrentWorldID())
        for entry in entries:
            result.append(entry.getName())
        return result

    def FuncCreateDocument(self, db, arguments):
        if arguments.get("name") is None:
            return self.funcError("missing argument")

        document = elements.Document(self.getCurrentWorldID())
        document.setName(arguments["name"])
        document = elements.createDocument(db, document)

        self.current_state = STATE_DOCUMENTS
        self.current_view = document.getElemTag()

        return self.funcStatus("Document created")

    def FuncUpdateDocument(self, db, arguments):
        if arguments.get("name") is None:
            return self.funcError("missing argument")

        document = elements.findDocument(
            db, self.getCurrentWorldID(), arguments["name"]
        )
        if document is None:
            return self.funcError("Document not found")

        self.current_state = STATE_DOCUMENTS
        self.current_view = document.getElemTag()

        if arguments.get("new_name"):
            document.setName(arguments["new_name"])
        elements.updateDocument(db, document)

        return self.funcStatus("Document updated")

    def FuncShowDocument(self, db, arguments):
        if arguments.get("name") is None:
            return self.funcError("missing argument")

        document = elements.findDocument(
            db, self.getCurrentWorldID(), arguments["name"]
        )
        if document is None:
            return self.funcError("Document not found")

        self.current_state = STATE_DOCUMENTS
        self.current_view = document.getElemTag()

        result = {"name": document.getName(), "headings": document.getSectionList()}
        return result

    def FuncAddDocumentSection(self, db, arguments):
        if (
            arguments.get("name") is None
            or arguments.get("heading") is None
            or arguments.get("content") is None
        ):
            return self.funcError("missing argument")

        document = elements.findDocument(
            db, self.getCurrentWorldID(), arguments["name"]
        )
        if document is None:
            return self.funcError("Document not found")

        document.addSection(arguments["heading"], arguments["content"])
        elements.updateDocument(db, document)
        element_info.UpdateElementInfo(db, document)

        return self.funcStatus("Document updated")

    def FuncReadDocumentSection(self, db, arguments):
        if arguments.get("name") is None or arguments.get("heading") is None:
            return self.funcError("missing argument")

        document = elements.findDocument(
            db, self.getCurrentWorldID(), arguments["name"]
        )
        if document is None:
            return self.funcError("Document not found")

        result = document.getSectionText(arguments["heading"])
        if result is None:
            return self.funcError("unknown heading")
        return {"heading": arguments["heading"], "content": result}

    def FuncUpdateDocumentSection(self, db, arguments):
        if (
            arguments.get("name") is None
            or arguments.get("heading") is None
            or arguments.get("content") is None
        ):
            return self.funcError("missing argument")

        document = elements.findDocument(
            db, self.getCurrentWorldID(), arguments["name"]
        )
        if document is None:
            return self.funcError("Document not found")

        document.updateSection(arguments["heading"], arguments["content"])
        if arguments.get("new_heading") is not None:
            document.updateHeading(arguments["heading"], arguments["new_heading"])
        elements.updateDocument(db, document)
        element_info.UpdateElementInfo(db, document)
        return self.funcStatus("Document updated")

    def FuncReadCharacter(self, db, arguments):
        if arguments.get("name") is None:
            return self.funcError("Missing argument 'name'")
        name = arguments.get("name")
        if name is None:
            return self.funcError("request missing name")

        character = elements.findCharacter(db, self.getCurrentWorldID(), name)
        if character is not None:
            content = {
                key: character.getAllProperties()[key]
                for key in DesignFunctions.CHAR_PROPS
            }
            content["has_image"] = character.hasImage()
            self.current_state = STATE_CHARACTERS
            self.current_view = character.getElemTag()
        else:
            return self.funcError(f"no character '{name}'")
        return content

    def FuncCreateCharacter(self, db, arguments):
        character = elements.Character(self.getCurrentWorldID())
        if arguments.get("name") is None:
            return self.funcError("Missing argument 'name'")
        character.setName(arguments["name"])

        characters = elements.listCharacters(db, self.getCurrentWorldID())
        name = checkDuplication(character.getName(), characters)
        if name is not None:
            return self.funcError(f"Similar name already exists: {name}")

        character.updateProperties(arguments)
        character = elements.createCharacter(db, character)
        self.current_view = character.getElemTag()
        self.current_state = STATE_CHARACTERS
        status = self.funcStatus("Created character")
        status["name"] = character.getName()
        element_info.UpdateElementInfo(db, character)
        return status

    def FuncUpdateCharacter(self, db, arguments):
        if arguments.get("name") is None:
            return self.funcError("Missing argument 'name'")

        name = arguments["name"]
        character = elements.findCharacter(db, self.getCurrentWorldID(), name)
        if character is None:
            return self.funcError(f"Character not found {name}")
        if arguments.get("new_name") is not None:
            arguments["name"] = arguments["new_name"]
        character.updateProperties(arguments)
        # TODO: check name collision
        elements.updateCharacter(db, character)
        self.modified = True
        self.current_view = character.getElemTag()
        status = self.funcStatus("Updated character")
        status["name"] = character.getName()
        element_info.UpdateElementInfo(db, character)
        return status

    def FuncReadItem(self, db, arguments):
        if arguments.get("name") is None:
            return self.funcError("Missing argument 'name'")

        name = arguments.get("name")
        if name is None:
            return self.funcError("request missing name parameter")

        item = elements.findItem(db, self.getCurrentWorldID(), name)
        if item is not None:
            content = {
                key: item.getAllProperties()[key] for key in DesignFunctions.ITEM_PROPS
            }
            content["has_image"] = item.hasImage()
            # TODO: change to name?
            # Remove site_id from view of GPT
            del content["ability"]["site_id"]

            # Translate site_id to site_name if necessary
            ability = item.getAbility()
            if ability.effect is not None and len(ability.site_id) > 0:
                site = elements.loadSite(db, ability.site_id)
                if site is not None:
                    content["ability"]["site"] = site.getName()

            self.current_state = STATE_ITEMS
            self.current_view = item.getElemTag()
        else:
            return self.funcError(f"no item '{name}'")
        return content

    def FuncCreateItem(self, db, arguments):
        item = elements.Item(self.getCurrentWorldID())
        item.setName(arguments["name"])

        items = elements.listItems(db, self.getCurrentWorldID())
        name = checkDuplication(item.getName(), items)
        if name is not None:
            return self.funcError(f"Similar name already exists: {name}")

        # Translate site name if necessary
        ability = arguments.get("ability")
        if ability is not None and ability.get("site") is not None:
            site_name = ability.get("site")
            site = elements.findSite(db, self.getCurrentWorldID(), site_name)
            if site is None:
                return self.funcError(f"Unknown site {site_name}")
            ability["site_id"] = site.getID()

        item.updateProperties(arguments)
        item = elements.createItem(db, item)
        element_info.UpdateElementInfo(db, item)
        self.current_view = item.getElemTag()
        self.current_state = STATE_ITEMS
        status = self.funcStatus("Created item")
        status["name"] = item.name
        return status

    def FuncUpdateItem(self, db, arguments):
        if arguments.get("name") is None:
            return self.funcError("Missing argument 'name'")
        name = arguments["name"]
        item = elements.findItem(db, self.getCurrentWorldID(), name)
        if item is None:
            return self.funcError(f"Item not found {name}")
        if arguments.get("new_name") is not None:
            arguments["name"] = arguments["new_name"]
        # TODO: check name collision

        ability = arguments.get("ability")
        if ability is not None:
            # Validate ability settings

            if ability.get("effect") is not None:
                if not ability["effect"] in [
                    item.value for item in elements.ItemEffect
                ]:
                    return self.funcError("Unknown effect: %s" % ability["effect"])

            if ability.get("site") is not None:
                # If present, translate site name to site id
                site_name = ability.get("site")
                site = elements.findSite(db, self.getCurrentWorldID(), site_name)
                if site is None:
                    return self.funcError(f"Unknown site {site_name}")
                ability["site_id"] = site.getID()

        # Update item proprties
        item.updateProperties(arguments)
        elements.updateItem(db, item)
        element_info.UpdateElementInfo(db, item)
        self.modified = True
        self.current_view = item.getElemTag()
        status = self.funcStatus("Updated item")
        status["name"] = item.getName()
        return status

    def FuncReadSite(self, db, arguments):
        if arguments.get("name") is None:
            return self.funcError("Missing argument 'name'")

        name = arguments.get("name")
        if name is None:
            return self.funcError("request missing name parameter")

        site = elements.findSite(db, self.getCurrentWorldID(), name)
        if site is not None:
            content = {
                key: site.getAllProperties()[key] for key in DesignFunctions.SITE_PROPS
            }
            self.current_state = STATE_SITES
            self.current_view = site.getElemTag()
        else:
            return self.funcError(f"no site '{name}'")
        return content

    def FuncCreateSite(self, db, arguments):
        site = elements.Site(self.getCurrentWorldID())
        if arguments.get("name") is None:
            return self.funcError("Missing argument 'name'")

        site.setName(arguments["name"])

        sites = elements.listSites(db, self.getCurrentWorldID())
        name = checkDuplication(site.getName(), sites)
        if name is not None:
            return self.funcError(f"Similar name already exists: {name}")

        site.updateProperties(arguments)
        site = elements.createSite(db, site)
        element_info.UpdateElementInfo(db, site)
        self.current_view = site.getElemTag()
        self.current_state = STATE_SITES
        status = self.funcStatus("Created site")
        status["name"] = site.getName()
        return status

    def FuncUpdateSite(self, db, arguments):
        if arguments.get("name") is None:
            return self.funcError("Missing argument 'name'")

        name = arguments["name"]
        site = elements.findSite(db, self.getCurrentWorldID(), name)
        if site is None:
            return self.funcError(f"Site not found {name}")
        if arguments.get("new_name") is not None:
            arguments["name"] = arguments["new_name"]
        site.updateProperties(arguments)
        # TODO: check name collision
        elements.updateSite(db, site)
        element_info.UpdateElementInfo(db, site)
        self.current_view = site.getElemTag()
        self.modified = True
        status = self.funcStatus("Updated site")
        status["name"] = site.getName()
        return status

    def FuncCreateImage(self, db, arguments):
        # Check if the budget allows
        if not chat_functions.check_image_budget(db):
            return self.funcError("No budget available for image creation")

        if arguments.get("prompt") is None:
            return self.funcError("Missing argument 'prompt'")

        image = elements.Image()
        image.setPrompt(arguments["prompt"])
        logging.info("Create image: prompt %s", image.prompt)

        if self.current_state == STATE_CHARACTERS:
            if arguments.get("name") is None:
                return self.funcError("Missing argument 'name'")

            name = arguments["name"]
            character = elements.findCharacter(db, self.getCurrentWorldID(), name)
            if character is None:
                return self.funcError(f"no character '{name}'")

            image.setParentId(character.getID())
            self.current_view = character.getElemTag()

        elif self.current_state == STATE_ITEMS:
            if arguments.get("name") is None:
                return self.funcError("Missing argument 'name'")

            name = arguments["name"]
            item = elements.findItem(db, self.getCurrentWorldID(), name)
            if item is None:
                return self.funcError(f"no item '{name}'")

            image.setParentId(item.getID())
            self.current_view = item.getElemTag()

        elif self.current_state == STATE_SITES:
            if arguments.get("name") is None:
                return self.funcError("Missing argument 'name'")

            name = arguments["name"]
            site = elements.findSite(db, self.getCurrentWorldID(), name)
            if site is None:
                return self.funcError(f"no site '{name}'")

            image.setParentId(site.getID())
            self.current_view = site.getElemTag()

        else:
            image.setParentId(self.getCurrentWorldID())

        if image.parent_id is None:
            logging.info("create image error: empty parent_id")
            return self.funcError("internal error - no id")

        dest_file = os.path.join(IMAGE_DIRECTORY, image.getFilename())
        logging.info("dest file: %s", dest_file)
        result = image_get_request(
            "Produce a visual image that captures the following: " + image.prompt,
            dest_file,
        )

        if result:
            logging.info("file create done, create image record")
            chat_functions.count_image(db, self.getCurrentWorldID(), 1)
            image = elements.createImage(db, image)
            create_image_thumbnail(image)
            self.modified = True
            status = self.funcStatus("created image")
            return status
        return self.funcError("problem generating image")

    def FuncRemoveElement(self, db, arguments):
        if arguments.get("name") is None:
            return self.funcError("Missing argument 'name'")

        name = arguments["name"]
        logging.info("Remove element: %s", name)
        # Change view
        self.current_view = self.getCurrentWorld(db).getElemTag()
        if self.current_state == STATE_CHARACTERS:
            if elements.hideCharacter(db, self.getCurrentWorldID(), name):
                return self.funcStatus("removed character")
            return self.funcError("character not found")

        if self.current_state == STATE_ITEMS:
            if elements.hideItem(db, self.getCurrentWorldID(), name):
                return self.funcStatus("removed item")
            return self.funcError("item not found")

        if self.current_state == STATE_SITES:
            if elements.hideSite(db, self.getCurrentWorldID(), name):
                return self.funcStatus("removed site")
            return self.funcError("site not found")
        return self.funcError("internal error")

    def FuncRecoverElements(self, db, arguments):
        world_id = self.getCurrentWorldID()
        logging.info("Recover elements for: %s", world_id)

        if self.current_state == STATE_CHARACTERS:
            count = elements.recoverCharacters(db, world_id)
            return self.funcStatus("Recovered %d characters" % count)
        if self.current_state == STATE_ITEMS:
            count = elements.recoverItems(db, world_id)
            return self.funcStatus("Recovered %d items" % count)
        if self.current_state == STATE_SITES:
            count = elements.recoverSites(db, world_id)
            return self.funcStatus("Recovered %d sites" % count)
        return self.funcError("internal error")

    def FuncRemoveImage(self, db, arguments):
        if arguments.get("index") is None:
            return self.funcError("Missing argument 'index'")

        index = arguments["index"]
        name = arguments.get("name")

        if self.current_state == STATE_WORLD_EDIT:
            element = self.getCurrentWorld(db)
        elif self.current_state == STATE_CHARACTERS:
            element = elements.findCharacter(db, self.getCurrentWorldID(), name)
        elif self.current_state == STATE_ITEMS:
            element = elements.findItem(db, self.getCurrentWorldID(), name)
        elif self.current_state == STATE_SITES:
            element = elements.findSite(db, self.getCurrentWorldID(), name)

        if element is None:
            return self.funcError("Unknown '%s'" % name)
        element_id = element.getID()

        logging.info("remove image element_id %s", element_id)
        logging.info("remove image index %s", index)

        iid = elements.getImageFromIndex(db, element_id, int(index))
        logging.info("remove image")

        if iid is None:
            return self.funcError(f"unknown image index: {index}")
        elements.hideImage(db, iid)
        return self.funcStatus("image removed")

    def FuncRecoverImages(self, db, arguments):
        if arguments.get("name") is None:
            return self.funcError("Missing argument 'name'")

        name = arguments.get("name")

        if self.current_state == STATE_WORLD_EDIT:
            element = self.getCurrentWorld(db)
        elif self.current_state == STATE_CHARACTERS:
            element = elements.findCharacter(db, self.getCurrentWorldID(), name)
        elif self.current_state == STATE_ITEMS:
            element = elements.findItem(db, self.getCurrentWorldID(), name)
        elif self.current_state == STATE_SITES:
            element = elements.findSite(db, self.getCurrentWorldID(), name)

        if element is None:
            return self.funcError("Unknown '%s'" % name)
        element_id = element.getID()

        count = elements.recoverImages(db, element_id)
        return self.funcStatus("Recovered %d images" % count)


def create_image_thumbnail(image_element):
    """
    Take an image element and create a thumbnail in the
    IMAGE_DIRECTORY
    """
    in_file = os.path.join(IMAGE_DIRECTORY, image_element.getFilename())
    out_file = os.path.join(IMAGE_DIRECTORY, image_element.getThumbName())
    image = Image.open(in_file)
    MAX_SIZE = (100, 100)
    image.thumbnail(MAX_SIZE)
    image.save(out_file)


def image_get_request(prompt, dest_file):
    # Testing stub. Just copy existing file.
    if TESTING:
        dir_name = os.path.dirname(__file__)
        path = os.path.join(dir_name, "static/logo.png")
        with open(dest_file, "wb") as fout:
            with open(path, "rb") as fin:
                fout.write(fin.read())
        return True

    # Functional code. Generate image and copy to dest_file.
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + openai.api_key,
    }
    json_data = {"model": "dall-e-3", "size": "1024x1024", "prompt": prompt}
    try:
        logging.info("post: %s", prompt)

        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json=json_data,
            timeout=60,
        )
        result = response.json()
        logging.info("image complete")
        if result.get("data") is None:
            return False

        response = requests.get(result["data"][0]["url"], stream=True, timeout=20)
        if response.status_code != 200:
            return False

        with open(dest_file, "wb") as f:
            response.raw.decode_content = True
            # Probably uses more memory than necessary
            # TODO: make more efficient
            f.write(response.raw.read())
        return True

    except Exception as e:
        logging.info("Unable to generate ChatCompletion response")
        logging.info("Exception: %s", str(e))
        raise e


all_functions = [
    {
        "name": "EditWorld",
        "description": "Enable editing of world properties.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "ChangeState",
        "description": "Change the current state for a new activity.",
        "parameters": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "The new state",
                },
            },
            "required": ["state"],
        },
    },
    {
        "name": "ListWorlds",
        "description": "Get a list of existing worlds.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "CreateWorld",
        "description": "Create a new virtual world",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the virtual world",
                },
                "description": {
                    "type": "string",
                    "description": "Short high level description of the virtual world",
                },
            },
            "required": ["name", "description"],
        },
    },
    {
        "name": "ShowWorld",
        "description": "Open and show a specific virtual world.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of world intance.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "UpdateWorld",
        "description": "Update the values of the virtual world.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the virtual world.",
                },
                "description": {
                    "type": "string",
                    "description": "Short high level description of the world.",
                },
                "details": {
                    "type": "string",
                    "description": "Detailed information about the virtual world.",
                },
                "plans": {
                    "type": "string",
                    "description": "Plans for developing characters, items, and sites.",
                },
            },
        },
    },
    {
        "name": "CreateWorldImage",
        "description": "Create an image for the current world",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "A prompt from which to create the image.",
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "ReadPlans",
        "description": "Read in the plans specific virtual world.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "UpdatePlans",
        "description": "Update the plans of the virtual world.",
        "parameters": {
            "type": "object",
            "properties": {
                "plans": {
                    "type": "string",
                    "description": "Plans for the virtual world.",
                },
            },
        },
    },
    {
        "name": "ListDocuments",
        "description": "Get list of background documents for the current world.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "CreateDocument",
        "description": "Create a new background document for the current world.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name for the document"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "ShowDocument",
        "description": "Show the document headings.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the document"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "AddDocumentSection",
        "description": "Add a section to the document.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the document"},
                "heading": {"type": "string", "description": "Section heading"},
                "content": {"type": "string", "description": "Section content"},
            },
            "required": ["name", "heading", "content"],
        },
    },
    {
        "name": "UpdateDocumentSection",
        "description": "Change a section in the document.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the document"},
                "heading": {"type": "string", "description": "Section heading"},
                "content": {"type": "string", "description": "Section content"},
            },
            "required": ["name", "heading", "content"],
        },
    },
    {
        "name": "ReadDocumentSection",
        "description": "Get the contents of a section in the document.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the document"},
                "heading": {"type": "string", "description": "Section heading"},
            },
            "required": ["name", "heading"],
        },
    },
    {
        "name": "UpdateDocument",
        "description": "Make changes to the document document.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the document"},
                "new_name": {
                    "type": "string",
                    "description": "New name of the document.",
                },
            },
            "required": ["name", "new_name"],
        },
    },
    {
        "name": "ListCharacters",
        "description": "Get a characters in the current world.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "CreateCharacter",
        "description": "Create a new character instance",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the character",
                },
                "description": {
                    "type": "string",
                    "description": "Short description of the character",
                },
            },
            "required": ["name", "description"],
        },
    },
    {
        "name": "ShowCharacter",
        "description": "Open and show a specific character.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the character.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "UpdateCharacter",
        "description": "Update the values of the character.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the character.",
                },
                "new_name": {
                    "type": "string",
                    "description": "New name of the character.",
                },
                "description": {
                    "type": "string",
                    "description": "Short description of the character",
                },
                "details": {
                    "type": "string",
                    "description": "Detailed information about the character.",
                },
                "personality": {
                    "type": "string",
                    "description": "Personality of the character.",
                },
                "appearance": {
                    "type": "string",
                    "description": "Character appearance.",
                },
                "traits": {
                    "type": "string",
                    "description": "Character traits.",
                },
                "behavior": {
                    "type": "string",
                    "description": "Character behavior.",
                },
                "relationships": {
                    "type": "string",
                    "description": "Relationships with other characters.",
                },
                "backstory": {
                    "type": "string",
                    "description": "Backstory for the character.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "RemoveCharacter",
        "description": "Remove a specific characvter.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the character.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "RecoverCharacters",
        "description": "Restore the characters for this world.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "CreateCharacterImage",
        "description": "Create an image for a specific character",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the character.",
                },
                "prompt": {
                    "type": "string",
                    "description": "A prompt from which to create the image.",
                },
            },
            "required": ["name", "prompt"],
        },
    },
    {
        "name": "ListItems",
        "description": "Get a items in the current world.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "CreateItem",
        "description": "Create a new item instance",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the item",
                },
                "description": {
                    "type": "string",
                    "description": "Short description of the item",
                },
                "details": {
                    "type": "string",
                    "description": "Detailed information about the item.",
                },
                "mobile": {
                    "type": "boolean",
                    "description": "True if item can be carried.",
                },
                "ability": {
                    "type": "object",
                    "description": "Abilities that the object enables.",
                    "properties": {
                        "effect": {
                            "type": "string",
                            "enum": [
                                "heal",
                                "hurt",
                                "paralize",
                                "poison",
                                "sleep",
                                "brainwash",
                                "capture",
                                "invisibility",
                                "open",
                            ],
                        },
                        "site": {
                            "type": "string",
                            "description": "Name of the site to unlock.",
                        },
                    },
                },
            },
            "required": ["name", "description"],
        },
    },
    {
        "name": "ShowItem",
        "description": "Open and show a specific item.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the item.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "UpdateItem",
        "description": "Update the values of the item.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the item.",
                },
                "new_name": {
                    "type": "string",
                    "description": "New name of the item.",
                },
                "description": {
                    "type": "string",
                    "description": "Short description of the item",
                },
                "details": {
                    "type": "string",
                    "description": "Detailed information about the item.",
                },
                "mobile": {
                    "type": "boolean",
                    "description": "True if item can be carried.",
                },
                "ability": {
                    "type": "object",
                    "description": "Abilities that the object enables.",
                    "properties": {
                        "effect": {
                            "type": "string",
                            "enum": [
                                "none",
                                "heal",
                                "hurt",
                                "paralize",
                                "poison",
                                "sleep",
                                "brainwash",
                                "capture",
                                "invisibility",
                                "unlock",
                            ],
                        },
                        "site": {
                            "type": "string",
                            "description": "Name of the site to unlock.",
                        },
                    },
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "RemoveItem",
        "description": "Remove a specific item.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the item.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "RecoverItems",
        "description": "Restore the items for this world.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "CreateItemImage",
        "description": "Create an image for a specific item",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the item.",
                },
                "prompt": {
                    "type": "string",
                    "description": "A prompt from which to create the image.",
                },
            },
            "required": ["name", "prompt"],
        },
    },
    {
        "name": "ListSites",
        "description": "Get a sites in the current world.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "CreateSite",
        "description": "Create a new site instance",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the site",
                },
                "description": {
                    "type": "string",
                    "description": "Short description of the site",
                },
            },
            "required": ["name", "description"],
        },
    },
    {
        "name": "ShowSite",
        "description": "Open and show a specific site.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the site.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "RemoveSite",
        "description": "Remove a specific site.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the site.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "RecoverSites",
        "description": "Restore the sites for this world.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "UpdateSite",
        "description": "Update the values of the site.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the site.",
                },
                "new_name": {
                    "type": "string",
                    "description": "New name of the site.",
                },
                "description": {
                    "type": "string",
                    "description": "Short description of the site",
                },
                "details": {
                    "type": "string",
                    "description": "Detailed information about the site.",
                },
                "default_open": {
                    "type": "boolean",
                    "description": "True if user can access the site.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "CreateSiteImage",
        "description": "Create an image for a specific site",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the site.",
                },
                "prompt": {
                    "type": "string",
                    "description": "A prompt from which to create the image.",
                },
            },
            "required": ["name", "prompt"],
        },
    },
    {
        "name": "RemoveImage",
        "description": "Remove an image from a character, site, or item",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the character, site, or item",
                },
                "index": {
                    "type": "integer",
                    "description": "Zero based index of image to remove",
                },
            },
            "required": ["name", "index"],
        },
    },
    {
        "name": "RecoverImages",
        "description": "Restore images for a character, site, or item",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the character, site, item.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "RemoveWorldImage",
        "description": "Remove an image from the world",
        "parameters": {
            "type": "object",
            "properties": {
                "index": {
                    "type": "integer",
                    "description": "Zero based index of image to remove",
                },
            },
            "required": ["index"],
        },
    },
    {
        "name": "RecoverWorldImages",
        "description": "Restore images for the world",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "SetStartCondition",
        "description": "Add a condition of the starting state",
        "parameters": {
            "type": "object",
            "properties": {
                "character": {
                    "type": "string",
                    "description": "Name of character"
                },
                "site": {
                    "type": "string",
                    "description": "Name of site"
                },
                "item": {
                    "type": "string",
                    "description": "Name of item"
                },
                "verb": {
                    "type": "string",
                    "enum": [
                        elements.ConditionVerb.AT,
                        elements.ConditionVerb.HAS,
                    ],
                }
            }
        }
    },
    {
        "name": "GetStartConditions",
        "description": "Get the list of configured starting conditions.",
        "parameters": {
        }
    }
]
