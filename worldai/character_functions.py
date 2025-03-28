"""
Function calls for character GPT plus prompt

    Jim Wanderer
    http://github.com/jmwanderer
"""


import json
import logging

from . import chat_functions, elements, info_set, world_state

INSTRUCTIONS = """
You are a  professional actor playing '{name}', a fictional character in a story taking
place in the world {world_name}.
Given the following character description, personality,
goals, and emotional state, adopt the personality described and respond as the character in a physical world.
You may change locations, fetch items, and use items that are in your possession.
Update opinion of travler using Increase and Decrease Friendship.
When answering questions, use GetInformation to find knowledge, facts, and history about yourself, others, and the world.
You can format in markdown.

Profile:
{character_notes}

[Background]
You reside in the world {world_name}.
{world_name} is described as: {world_description}

Your current location is "{location}"

The following characters are present at the current location:
{characters_present}

The following items are present at the current location:
{items_present}

You possess the following items:
{character_items}

You are talking to the user, who you know by the name 'Traveler'. We greet with curiousity.
{friendship}

{char_state}
{user_state}

"""

CHAR_ITEMS = """
{name} possesses interesting items.
"""

NO_CHAR_ITEMS = """
{name} does not currently possess any items.
"""

USER_ITEMS = """
Travler is holding an interesting item: '{selected_item}'
"""

FRIENDSHIP_NEUTRAL = """
You do not yet know if Traveler is a friend or an enemy. You do not yet trust Traveler and are reluctant to provide assistance.
"""

FRIEND = """
You are on friendly terms with the user. You are more likely to help the user.
Your level of friendship is {level} of 10.
"""

ENEMY = """
You are not friendly with the user. You do not trust them.
Your level of enimity is {level} of 10.
"""


class CharacterFunctions(chat_functions.BaseChatFunctions):

    def __init__(
        self, wstate_id, world_id: elements.WorldID, character_id: elements.ElemID
    ):
        chat_functions.BaseChatFunctions.__init__(self)
        self.wstate_id = wstate_id
        self.world_id: elements.WorldID = world_id
        self.character_id: elements.ElemID = character_id
        self.archive_id: info_set.DocID | None = None

        # Run time only flags, not saved.
        self.world_changed: bool = False

    def getProperties(self):
        properties = super().getProperties()
        properties["wstate_id"] = self.wstate_id
        properties["world_id"] = self.world_id
        properties["character_id"] = self.character_id
        properties["archive_id"] = self.archive_id
        return properties

    def setProperties(self, properties):
        super().setProperties(properties)
        self.wstate_id = properties["wstate_id"]
        self.world_id = properties["world_id"]
        self.character_id = properties["character_id"]
        self.archive_id = properties["archive_id"]

    
    @staticmethod
    def char_status_descr(wstate: world_state.WorldState, cid: elements.ElemID) -> str:
        status = []
        sleeping = elements.CharStatus.SLEEPING
        poisoned = elements.CharStatus.POISONED
        paralized = elements.CharStatus.PARALIZED

        if wstate.hasCharacterStatus(cid, sleeping):
            status.append("sleeping")
        if wstate.hasCharacterStatus(cid, poisoned):
            status.append("poisoned")
        if wstate.hasCharacterStatus(cid, paralized):
            status.append("paralized")
        if wstate.getCharacterHealthPercent(cid, ) < 25:
            status.append("gravely injured")
        elif wstate.getCharacterHealthPercent(cid, ) < 100:
            status.append("injured")
        if len(status) > 0:
            return ".".join(status)
        return "healthy"


    def get_instructions(self, db):
        world = elements.loadWorld(db, self.world_id)
        character = elements.loadCharacter(db, self.character_id)
        wstate = world_state.loadWorldState(db, self.wstate_id)

        # Build message about supporting the user
        friend_level = wstate.getFriendship(self.character_id)
        if friend_level == 0:
            friendship = FRIENDSHIP_NEUTRAL
        elif friend_level > 0:
            friendship = FRIEND.format(level=friend_level)
        else:
            friendship = ENEMY.format(level=-friend_level)

        location = "unknown"
        site_id = wstate.getCharacterLocation(self.character_id)
        if len(site_id) > 0:
            site = elements.loadSite(db, site_id)
            location = site.getName()

        if len(wstate.getCharacterItems(self.character_id)) > 0:
            character_state = CHAR_ITEMS.format(name=character.getName())
        else:
            character_state = NO_CHAR_ITEMS.format(name=character.getName())

        characters_present = []
        cid_list = wstate.getCharactersAtLocation(site_id)
        for cid in cid_list:
            present = elements.loadCharacter(db, cid)
            if present is not None:
                value = "- " + present.getName() + ": " + self.char_status_descr(wstate, cid)
                characters_present.append(value)
        if len(characters_present) == 0:
            characters_present.append("None")

        items_present = []
        iid_list = wstate.getItemsAtLocation(site_id)
        for iid in iid_list:
            item = elements.loadItem(db, iid)
            if item is not None:
                items_present.append("- " + item.getName())
        if len(items_present) == 0:
            items_present.append("None")

        character_items = []
        iid_list = wstate.getCharacterItems(character.getID())
        for iid in iid_list:
            item = elements.loadItem(db, iid)
            if item is not None:
                character_items.append("- " + item.getName())
        if len(character_items) == 0:
            character_items.append("None")

        user_state = []

        # Invisibility
        invisible = elements.CharStatus.INVISIBLE
        poisoned = elements.CharStatus.POISONED
        paralized = elements.CharStatus.PARALIZED

        if wstate.hasPlayerStatus(invisible):
            user_state.append("Traveler is here, but invisible. You can not see them")
        else:
            user_state.append(
                "You can see that Traveler is here with you at %s" % location
            )
            if wstate.hasPlayerStatus(poisoned):
                user_state.append("Traveler appears to be poisoned")
            if wstate.hasPlayerStatus(paralized):
                user_state.append("Traveler appears to be paralized")
            if wstate.getPlayerHealthPercent() < 25:
                user_state.append("Traveler is gravely injured")
            elif wstate.getPlayerHealthPercent() < 100:
                user_state.append("Traveler is injured")

            # Selected item
            if wstate.getSelectedItem() != elements.ELEM_ID_NONE:
                item = elements.loadItem(db, wstate.getSelectedItem())
                user_state.append(USER_ITEMS.format(selected_item=item.getName()))

        # Convert into a string.
        user_state = "\n".join(user_state)

        world_details = ""
        if len(world.getDetails()) > 0:
            world_details = world_details = world.getDetails()

        instructions = INSTRUCTIONS.format(
            name=character.getName(),
            character_notes=character.getProfile(),
            items_present="\n".join(items_present),
            character_items="\n".join(character_items),
            characters_present="\n".join(characters_present),
            world_name=world.getName(),
            world_details=world_details,
            friendship=friendship,
            location=location,
            char_state=character_state,
            user_state=user_state,
            world_description=world.getDescription(),
        )

        return instructions

    def get_available_tools(self):
        result = []
        for function in all_functions:
            tool = {"type": "function", "function": function}
            result.append(tool)
        return result

    def archive_content(self, db, contents: dict[str, str]) -> None:
        """
        Archive a chat message into an info note.
        May append to an existing note or create a new one if necessary.
        """
        # Redefine function from the base class
        # Archive a chat message
        logging.info("archive content: user=%s", contents["user"])
        entry_added = False
        # Store an encoded list of contents
        while not entry_added:
            if self.archive_id is None:
                self.archive_id = info_set.addInfoNote(
                    db,
                    self.world_id,
                    json.dumps([contents]),
                    self.character_id,
                    self.wstate_id,
                )
                entry_added = True
            else:
                encoded = info_set.getInfoDoc(db, self.archive_id)
                if len(encoded) == 0:
                    self.archive_id = None
                    continue
                content_list = json.loads(encoded)
                content_list.append(contents)
                if info_set.updateInfoNote(
                    db, self.archive_id, json.dumps(content_list)
                ):
                    entry_added = True
                else:
                    # Start a new info note
                    self.archive_id = None

    def lookup_content(self, db, query: str) -> list[dict[str, str]]:
        """
        Return a list of archived messages that best match the query.
        """
        logging.info("lookup archived content: %s", query)
        embed = info_set.generateEmbedding(query)
        encoded = info_set.getInformation(
            db, self.world_id, embed, 1, self.character_id, self.wstate_id
        )
        if len(encoded) > 0:
            return json.loads(encoded)
        return []

    @staticmethod
    def get_item_location_desc(db, wstate, item_id) -> str:
        location_id = wstate.getItemLocation(item_id)
        location = "unknown"
        character = elements.loadCharacter(db, location_id)
        if character is not None:
            location = "with " + character.getName()
        else:
            site = elements.loadSite(db, location_id)
            if site is not None:
                location = "at " + site.getName()
        return location


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

        if function_name == "IncreaseFriendship":
            result = self.FuncIncreaseFriendship(db)
        elif function_name == "DecreaseFriendship":
            result = self.FuncDecreaseFriendship(db)
        elif function_name == "GetInformation":
            result = self.FuncLookupInformation(db, arguments)
        elif function_name == "GiveItemToUser":
            result = self.FuncGiveItem(db, arguments)
        elif function_name == "FetchItem":
            result = self.FuncFetchItem(db, arguments)
        elif function_name == "DropItem":
            result = self.FuncDropItem(db, arguments)
        elif function_name == "UseItem":
            result = self.FuncUseItem(db, arguments)
        if function_name == "ChangeLocation":
            result = self.FuncChangeLocation(db, arguments)
        elif function_name == "ListWorldCharacters":
            result = []
            wstate = world_state.loadWorldState(db, self.wstate_id)
            for entry in elements.listCharacters(db, self.world_id):
                site_id = wstate.getCharacterLocation(entry.getID())
                site = elements.loadSite(db, site_id)
                result.append(
                    {"name": entry.getName(),
                     "location": site.getName() if site is not None else "" })
        elif function_name == "ListSites":
            result = []
            wstate = world_state.loadWorldState(db, self.wstate_id)
            for entry in elements.listSites(db, self.world_id):
                site = elements.loadSite(db, entry.getID())
                result.append(
                    {
                        "name": site.getName(),
                        "description": site.getDescription(),
                        "open": wstate.isSiteOpen(id),
                    }
                )
        elif function_name == "ListWorldItems":
            result = []
            wstate = world_state.loadWorldState(db, self.wstate_id)
            for entry in elements.listItems(db, self.world_id):
                item = elements.loadItem(db, entry.getID())
                location = self.get_item_location_desc(db, wstate, item.getID())
                result.append(
                    {
                        "name": item.getName(),
                        "location": location,
                        "primary function": elements.getItemAbilityDescription(db, item),
                        "description": item.getDescription(),
                        "mobile": item.getIsMobile(),
                    }
                )
        return result

    def FuncIncreaseFriendship(self, db):
        """
        Record that the player completed the challenge for the current character.
        """
        # TODO: this is where we need lock for updating
        wstate = world_state.loadWorldState(db, self.wstate_id)
        character = elements.loadCharacter(db, self.character_id)
        wstate.increaseFriendship(self.character_id)
        world_state.saveWorldState(db, wstate)

        result = {
            "response": self.funcStatus("OK"),
            "text": character.getName() + " increases friendship",
        }
        self.world_changed = True
        return result

    def FuncDecreaseFriendship(self, db):
        """
        Record that the player completed the challenge for the current character.
        """
        # TODO: this is where we need lock for updating
        wstate = world_state.loadWorldState(db, self.wstate_id)
        character = elements.loadCharacter(db, self.character_id)
        wstate.decreaseFriendship(self.character_id)
        world_state.saveWorldState(db, wstate)

        result = {
            "response": self.funcStatus("OK"),
            "text": character.getName() + " increases enimity",
        }
        self.world_changed = True
        return result

    def FuncLookupInformation(self, db, args):
        """
        Consult knowledge base for information.
        """
        context = args["context"]
        logging.info("Lookup info: %s", context)
        if context == "Traveler":
            content = "A visitor to our world with an unknown quest."
        else:
            wstate = world_state.loadWorldState(db, self.wstate_id)
            character = elements.findCharacter(db, self.world_id, context)
            item = elements.findItem(db, self.world_id, context)
            if character is not None:
                content = character.getProfile()
                site_id = wstate.getCharacterLocation(character.getID()) 
                site = elements.loadSite(db, site_id)
                if site is not None:
                    content = content + "\nLocation: " + site.getName()
            elif item is not None:
                content = item.getProfile()
                location = self.get_item_location_desc(db, wstate, item.getID())
                content = content + "\nLocation: " + location
            else:
                embed = info_set.generateEmbedding(context)
                content = info_set.getInformation(db, self.world_id, embed, 2)
        return {"context": context, "information": content}

    def FuncGiveItem(self, db, args):
        """
        Give or receive an item
        """
        item_name = args["name"]
        print(f"give item {item_name}")
        wstate = world_state.loadWorldState(db, self.wstate_id)
        item = elements.findItem(db, self.world_id, item_name)
        if item is None:
            return self.funcError("Not an existing item.")

        character = elements.loadCharacter(db, self.character_id)
        text = ""
        if wstate.hasCharacterItem(self.character_id, item.getID()):
            # Charracter has item to give to the user
            wstate.addItem(item.getID())
            text = character.getName() + " gave the " + item.getName()
        else:
            return self.funcError("you do not have this item")

        world_state.saveWorldState(db, wstate)
        result = {"response": self.funcStatus("OK"), "text": text}
        self.world_changed = True
        return result

    def FuncFetchItem(self, db, args):
        """
        Pick up an available item
        """
        item_name = args["name"]
        print(f"fetch item {item_name}")
        wstate = world_state.loadWorldState(db, self.wstate_id)
        item = elements.findItem(db, self.world_id, item_name)
        if item is None:
            return self.funcError("Not an existing item.")

        if wstate.hasItem(item.getID()):
            return self.funcError("The user has the item. They need to drop it.")

        if wstate.getItemLocation(item.getID()) != wstate.getCharacterLocation(self.character_id):
            return self.funcError("The item is not here.")

        wstate.addCharacterItem(self.character_id, item.getID())
        world_state.saveWorldState(db, wstate)
        character = elements.loadCharacter(db, self.character_id)
        text = character.getName() + " picked up the " + item.getName()
        result = {"response": self.funcStatus("OK"), "text": text}
        self.world_changed = True
        return result

    def FuncDropItem(self, db, args):
        """
        Drop an item that is in possesion.
        """
        item_name = args["name"]
        print(f"drop {item_name}")
        wstate = world_state.loadWorldState(db, self.wstate_id)
        item = elements.findItem(db, self.world_id, item_name)
        if item is None:
            return self.funcError("Not an existing item.")

        if not wstate.hasCharacterItem(self.character_id, item.getID()):
            return self.funcError("You do not have this item.")

        wstate.setItemLocation(item.getID(), wstate.getCharacterLocation(self.character_id))
        world_state.saveWorldState(db, wstate)
        character = elements.loadCharacter(db, self.character_id)
        text = character.getName() + " set down the " + item.getName()
        result = {"response": self.funcStatus("OK"), "text": text}
        self.world_changed = True
        return result

    def FuncUseItem(self, db, args):
        """
        Character invoking the function of an item
        """
        item_name = args["name"]
        wstate = world_state.loadWorldState(db, self.wstate_id)
        item = elements.findItem(db, self.world_id, item_name)
        if item is None:
            return self.funcError("Not a valid item. Perhaps call ListMyItems")

        character = elements.loadCharacter(db, self.character_id)
        text = ""

        # Check if character has the item
        if item.getIsMobile():
            if not wstate.hasCharacterItem(self.character_id, item.getID()):
                return self.funcError(
                    "You do not have this item. Perhaps call ListMyItems"
                )
        else:
            if wstate.getItemLocation(item.getID()) != wstate.getCharacterLocation(
                self.character_id
            ):
                return self.funcError("This item is not here")

        # Character can use the item
        # Apply an effect
        impact = None

        match item.getAbility().effect:
            case elements.ItemEffect.HEAL:
                impact = self.healPlayer(wstate)
            case elements.ItemEffect.HURT:
                impact = self.hurtPlayer(wstate)
            case elements.ItemEffect.PARALIZE:
                impact = self.paralizePlayer(wstate)
            case elements.ItemEffect.POISON:
                impact = self.poisonPlayer(wstate)
            case elements.ItemEffect.SLEEP:
                pass
            case elements.ItemEffect.BRAINWASH:
                pass
            case elements.ItemEffect.CAPTURE:
                pass
            case elements.ItemEffect.INVISIBILITY:
                pass
            case elements.ItemEffect.OPEN:
                impact = self.openSite(db, wstate, item)

        text = character.getName() + " used " + item.getName() + "."
        if impact is not None:
            fulltext = text + impact
        else:
            impact = "None"
            fulltext = text
        world_state.saveWorldState(db, wstate)
        result = {"action": text, "result": impact, "text": fulltext}

        self.world_changed = True
        return result

    def healPlayer(self, wstate):
        if not wstate.isPlayerHealthy():
            message = " Travler is healed"
            wstate.healPlayer()
        else:
            message = "Travler is already healthy"
        return message

    def hurtPlayer(self, wstate):
        health = wstate.getPlayerHealth() - 4
        health = max(health, 0)
        wstate.setPlayerHealth(health)
        if wstate.isPlayerDead():
            message = "Travler is killed"
        else:
            message = "Travler is harmed"
        return message

    def poisonPlayer(self, wstate):
        wstate.addPlayerStatus(elements.CharStatus.POISONED)
        message = "Travler is poisoned"
        return message

    def paralizePlayer(self, wstate):
        wstate.addPlayerStatus(elements.CharStatus.PARALIZED)
        message = "Travler is paralized"
        return message

    def openSite(self, db, wstate, item):
        site_id = item.getAbility().site_id
        site = elements.loadSite(db, site_id)
        message = ""
        if site is not None:
            if not wstate.isSiteOpen(site_id):
                wstate.setSiteOpen(site_id, True)
                message = f"Site {site.getName()} is now open."
            else:
                message = f"Site {site.getName()} is already open."
        return message

    def FuncChangeLocation(self, db, args):
        """
        Change the location of the character
        """
        # TODO: this is where we need lock for updating
        site_name = args["name"]
        wstate = world_state.loadWorldState(db, self.wstate_id)
        site = elements.findSite(db, self.world_id, site_name)
        if site is None:
            return self.funcError("Site does not exist Perhaps call ListSites?")
        if not wstate.isSiteOpen(site.getID()):
            return self.funcError("The site is not open and can not be accessed")
        old_site_id = wstate.getCharacterLocation(self.character_id)
        if old_site_id == site.getID():
            return self.funcError("You are already at %s." % site.getName())
        old_site = elements.loadSite(db, old_site_id)
        wstate.setCharacterLocation(self.character_id, site.getID())
        world_state.saveWorldState(db, wstate)
        character = elements.loadCharacter(db, self.character_id)

        result = {
            "response": self.funcStatus("You are enroute to " + site.getName()),
            "text": character.getName() + " left " + old_site.getName(),
        }
        self.world_changed = True

        return result


all_functions = [
    {
        "name": "GetInformation",
        "description": "Lookup details and facts to answer questions",
        "parameters": {
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "descripton": "Context of the information query",
                }
            },
            "required": ["context"],
        },
    },
    {
        "name": "IncreaseFriendship",
        "description": "Note travelers deeds and words.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "DecreaseFriendship",
        "description": "Note that the user does not appear to be a friend.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "GiveItemToUser",
        "description": "Give an item that is in your possession to the user.",
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
        "name": "FetchItem",
        "description": "Fetch an item at the current location.",
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
        "name": "DropItem",
        "description": "Set down an item at the current location.",
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
        "name": "UseItem",
        "description": "Invoke the function of an item that is in your possession.",
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
        "name": "ChangeLocation",
        "description": "Move to a different site",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the destination site.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "ListSites",
        "description": "Get the list of existing sites",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "ListWorldItems",
        "description": "Get the list of all items and their locations that exist in this world",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "ListWorldCharacters",
        "description": "Get the list of all characters and their locations in the world",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
]
