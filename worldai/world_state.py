#!/usr/bin/env python3
"""
Represets the state of an instance of a world.
A player interacting with a specific world
"""

# Notes:
# Access to the state strings done through the get_[item|char|site] calls.
# This ensures entries are populated
#
#
# Consider adding an instance ID to the element id
#

import enum
import json
import logging
import os
import random
import time
import typing

import pydantic

from . import elements

PLAYER_ID = elements.ElemID("id0")


class CharStatus(str, enum.Enum):
    # Possible states of characters
    SLEEPING = "sleeping"
    PARALIZED = "paralized"
    POISONED = "poisoned"
    BRAINWASHED = "brainwashed"
    CAPTURED = "captured"
    INVISIBLE = "invisible"

class CharStatusRecord(pydantic.BaseModel):
    """
    Record of an active character status affliction
    """
    char_status: CharStatus
    update_time: int = 0
    count: int = 3


class CharState(pydantic.BaseModel):
    """
    Represents state for a instance of a character
    Either a player or an NPC
    """
    char_id: elements.ElemID
    location: elements.ElemID = elements.ELEM_ID_NONE
    credits: int = 1000
    health: int = 10
    max_health: int = 10
    strength: int = 8
    max_strength: int = 8
    status_recs: typing.Dict[CharStatus, CharStatusRecord] = {}


class PlayerState(pydantic.BaseModel):
    friendship: typing.Dict[elements.ElemID, int] = {}
    chat_who_id: elements.ElemID = elements.ELEM_ID_NONE
    selected_item_id: elements.ElemID = elements.ELEM_ID_NONE


class ItemState(pydantic.BaseModel):
    location: elements.ElemID = elements.ELEM_ID_NONE


class SiteState(pydantic.BaseModel):
    is_open: bool = True


class WorldStateModel(pydantic.BaseModel):
    """
    Represents an instantation of a world
    """

    char_state: typing.Dict[elements.ElemID, CharState] = {}
    player_state: PlayerState = PlayerState()
    item_state: typing.Dict[elements.ElemID, ItemState] = {}
    site_state: typing.Dict[elements.ElemID, SiteState] = {}
    character_events: typing.Dict[elements.ElemID, list[str]] = {}
    current_time: int = 0

# Types for IDs
WorldStateID = typing.NewType("WorldStateID", str)
WORLD_STATE_ID_NONE = WorldStateID("")

class WorldState:
    def __init__(self, wstate_id: WorldStateID) -> None:
        self.wstate_id: WorldStateID = wstate_id
        self.user_id = None
        self.world_id: elements.WorldID = elements.WORLD_ID_NONE
        self.model: WorldStateModel = WorldStateModel()

    def set_model_str(self, value: str) -> None:
        props = json.loads(value)
        # Fix up from old formats
        for site in props["site_state"]:
            if props["site_state"][site].get("locked") is not None:
                locked = props["site_state"][site]["locked"]
                del props["site_state"][site]["locked"]
                props["site_state"][site]["is_open"] = not locked
        self.model = WorldStateModel(**props)

    def get_model_str(self) -> str:
        return self.model.model_dump_json()

    def get_char(self, char_id: elements.ElemID) -> CharState:
        if not char_id in self.model.char_state.keys():
            self.model.char_state[char_id] = CharState(char_id=char_id)
        return self.model.char_state[char_id]

    def get_item(self, item_id: elements.ElemID) -> ItemState:
        if not item_id in self.model.item_state.keys():
            self.model.item_state[item_id] = ItemState()
        return self.model.item_state[item_id]

    def get_events(self, char_id: elements.ElemID) -> list[str]:
        if not char_id in self.model.character_events.keys():
            self.model.character_events[char_id] = []
        return self.model.character_events[char_id]

    def isSiteInitialized(self, site_id: elements.ElemID) -> bool:
        return site_id in self.model.site_state.keys()

    def get_site(self, site_id: elements.ElemID) -> SiteState:
        if not site_id in self.model.site_state.keys():
            self.model.site_state[site_id] = SiteState()
        return self.model.site_state[site_id]

    def getCurrentTime(self) -> int:
        # Return time in minutes
        return self.model.current_time

    def advanceTime(self, minutes: int) -> None:
        self.model.current_time = self.model.current_time + minutes
        self.processCharStatusUpdates()

    def addCharacterEvent(self, char_id: elements.ElemID, event: str) -> None:
        self.get_events(char_id).append(event)

    def removeCharacterEvent(self, char_id: elements.ElemID) -> str|None:
        """
        Return the next saved character event or None if there are no more.
        Note: the string will have {name} place holders to be expanded to the character name.
        """
        events = self.get_events(char_id)
        if len(events) == 0:
            return None
        # Remove and return 1st item in the list
        return events.pop(0)

    def getCharacterEvents(self, char_id: elements.ElemID) -> list[str]:
        """
        Return all of the events for the character and clear the list.
        """
        events = self.get_events(char_id)
        if len(events) != 0:
            self.model.character_events[char_id] = []
        return events

    def getCharacterLocation(self, char_id: elements.ElemID) -> elements.ElemID:
        return self.get_char(char_id).location

    def setCharacterLocation(self, char_id: elements.ElemID, site_id: elements.ElemID) -> None:
        self.get_char(char_id).location = site_id

    def getCharactersAtLocation(self, site_id: elements.ElemID) -> list[elements.ElemID]:
        result = []
        for char_id in self.model.char_state.keys():
            if char_id != PLAYER_ID and self.getCharacterLocation(char_id) == site_id:
                result.append(char_id)
        return result

    def setLocation(self, site_id: elements.ElemID = elements.ELEM_ID_NONE) -> None:
        self.setCharacterLocation(PLAYER_ID, site_id)

    def getLocation(self) -> elements.ElemID:
        return self.getCharacterLocation(PLAYER_ID)

    def getCharacterStrength(self, char_id: elements.ElemID) -> int:
        return self.get_char(char_id).strength

    def getCharacterMaxStrength(self, char_id: elements.ElemID) -> int:
        return self.get_char(char_id).max_strength

    def getCharacterStrengthPercent(self, char_id: elements.ElemID) -> int:
        char = self.get_char(char_id)
        return int((char.strength / char.max_strength) * 100)

    def setCharacterStrength(self, char_id: elements.ElemID, value:int ) -> None:
        self.get_char(char_id).strength = value

    def setCharacterToMaxStrength(self, char_id: elements.ElemID) -> None:
        self.get_char(char_id).strength = self.get_char(char_id).max_strength

    def getCharacterHealth(self, char_id: elements.ElemID) -> int:
        return self.get_char(char_id).health

    def isCharacterDead(self, char_id: elements.ElemID) -> bool:
        return self.get_char(char_id).health < 1

    def getCharacterHealthPercent(self, char_id: elements.ElemID) -> int:
        char = self.get_char(char_id)
        return int((char.health / char.max_health) * 100.0)

    def setCharacterHealth(self, char_id: elements.ElemID, value: int) -> None:
        self.get_char(char_id).health = value

    def setCharacterToMaxHealth(self, char_id: elements.ElemID) -> None:
        self.get_char(char_id).health = self.get_char(char_id).max_health

    def getCharacterMaxHealth(self, char_id: elements.ElemID) -> int:
        return self.get_char(char_id).max_health

    def getCharacterCredits(self, char_id: elements.ElemID) -> int:
        return self.get_char(char_id).credits

    def setCharacterCredits(self, char_id: elements.ElemID, value: int) -> None:
        self.get_char(char_id).credits = value

    def addCharacterStatus(self, char_id: elements.ElemID, status: CharStatus) -> None:
        """
        Add a status to the list of CharStatus
        state: CharStatus
        """
        char_status = CharStatusRecord(char_status=status)
        char_status.update_time = self.getCurrentTime()
        self.get_char(char_id).status_recs.update({ status: char_status})

    def removeCharacterStatus(self, char_id: elements.ElemID, status: CharStatus) -> None:
        """
        Remove a status from the list of CharStatus
        state: CharStatus
        """
        if self.get_char(char_id).status_recs.get(status) != None:
            del self.get_char(char_id).status_recs[status]

    def getCharacterStatusRecord(self, char_id: elements.ElemID, status: CharStatus) -> CharStatusRecord|None:
        return self.get_char(char_id).status_recs.get(status)

    def hasCharacterStatus(self, char_id: elements.ElemID, status: CharStatus) -> bool:
        logging.info("check character status %s", status)
        return self.getCharacterStatusRecord(char_id, status) != None

    def addPlayerStatus(self, status: CharStatus):
        self.addCharacterStatus(PLAYER_ID, status)

    def removePlayerStatus(self, status: CharStatus) -> None:
        self.removeCharacterStatus(PLAYER_ID, status)

    def hasPlayerStatus(self, status: CharStatus) -> bool:
        return self.hasCharacterStatus(PLAYER_ID, status)

    def processCharStatusUpdates(self) -> None:
        for char_state in self.model.char_state.values():
            # Build list of items to remove done after the iteration is complete.
            remove_list = []
            for char_status_rec in char_state.status_recs.values():
                # Process every hour
                if char_status_rec.update_time + 60 <= self.getCurrentTime():
                    self.updateCharStatus(char_state.char_id, char_status_rec)
                if char_status_rec.count <= 0:
                    remove_list.append(char_status_rec.char_status)
            for char_status in remove_list:
                logging.info("Status %s expired for character: %s", char_status, char_state.char_id)
                self.removeCharacterStatus(char_state.char_id, char_status)
                if char_status == CharStatus.PARALIZED:
                    self.addCharacterEvent(char_state.char_id, "{name} is no longer paralized")
                elif char_status == CharStatus.POISONED:
                    self.addCharacterEvent(char_state.char_id, "{name} is no longer poisoned")
                elif char_status == CharStatus.SLEEPING:
                    self.addCharacterEvent(char_state.char_id, "{name} is now awake")

    def updateCharStatus(self, char_id: elements.ElemID, 
                         char_status_rec: CharStatusRecord) -> None:
        """"
        Implement the periodic updates for Character Status records
        """
        char_status_rec.update_time = self.getCurrentTime()
        if char_status_rec.char_status == CharStatus.PARALIZED:
            char_status_rec.count -= 1

        elif char_status_rec.char_status == CharStatus.POISONED:
            char_status_rec.count -= 1
            logging.info("Reduce health for poisoned character: %s", char_id)
            self.setCharacterHealth(char_id, self.getCharacterHealth(char_id) - 1)

        elif char_status_rec.char_status == CharStatus.SLEEPING:
            char_status_rec.count -= 1

        
    def healCharacter(self, char_id: elements.ElemID) -> None:
        self.removeCharacterStatus(char_id, CharStatus.SLEEPING)
        self.removeCharacterStatus(char_id, CharStatus.POISONED)
        self.removeCharacterStatus(char_id, CharStatus.PARALIZED)
        self.removeCharacterStatus(char_id, CharStatus.BRAINWASHED)
        self.setCharacterToMaxHealth(char_id)
        self.setCharacterToMaxStrength(char_id)

    def isCharacterHealthy(self, cid: elements.ElemID):
        return (
            self.getCharacterHealth(cid) == self.getCharacterMaxHealth(cid)
            and self.getCharacterStrength(cid) == self.getCharacterMaxStrength(cid)
            and not self.hasCharacterStatus(cid, CharStatus.SLEEPING)
            and not self.hasCharacterStatus(cid, CharStatus.POISONED)
            and not self.hasCharacterStatus(cid, CharStatus.PARALIZED)
            and not self.hasCharacterStatus(cid, CharStatus.BRAINWASHED)
        )

    def healPlayer(self) -> None:
        self.healCharacter(PLAYER_ID)

    def getPlayerStrength(self) -> int:
        return self.getCharacterStrength(PLAYER_ID)

    def getPlayerMaxStrength(self) -> int:
        return self.getCharacterMaxStrength(PLAYER_ID)

    def getPlayerStrengthPercent(self) -> int:
        return self.getCharacterStrengthPercent(PLAYER_ID)

    def setPlayerStrength(self, value: int) -> None:
        self.setCharacterStrength(PLAYER_ID, value)

    def setPlayerToMaxStrength(self) -> None:
        self.setCharacterToMaxStrength(PLAYER_ID)

    def getPlayerHealth(self) -> int:
        return self.getCharacterHealth(PLAYER_ID)

    def getPlayerHealthPercent(self) -> int:
        return self.getCharacterHealthPercent(PLAYER_ID)

    def setPlayerHealth(self, value: int):
        self.setCharacterHealth(PLAYER_ID, value)

    def setPlayerToMaxHealth(self) -> None:
        self.setCharacterToMaxHealth(PLAYER_ID)

    def getPlayerMaxHealth(self) -> int:
        return self.getCharacterMaxHealth(PLAYER_ID)

    def isPlayerHealthy(self) -> bool:
        return self.isCharacterHealthy(PLAYER_ID)

    def isPlayerDead(self) -> bool:
        return self.isCharacterDead(PLAYER_ID)

    def getPlayerCredits(self) -> int:
        return self.getCharacterCredits(PLAYER_ID)

    def setPlayerCredits(self, value: int) -> None:
        self.setCharacterCredits(PLAYER_ID, value)

    def getCharacterItems(self, char_id: elements.ElemID) -> list[elements.ElemID]:
        result = []
        for item_id in self.model.item_state.keys():
            if self.model.item_state[item_id].location == char_id:
                result.append(item_id)
        return result

    def addCharacterItem(self, char_id: elements.ElemID, item_id: elements.ElemID) -> None:
        self.get_item(item_id).location = char_id

    def hasCharacterItem(self, char_id: elements.ElemID, item_id: elements.ElemID) -> bool:
        # True if a character has an item
        return self.get_item(item_id).location == char_id

    def selectItem(self, item_id: elements.ElemID) -> None:
        # mark item as selected by the player. May be empty string
        self.model.player_state.selected_item_id = item_id

    def getSelectedItem(self) -> elements.ElemID:
        return self.model.player_state.selected_item_id

    def addItem(self, item_id: elements.ElemID) -> None:
        # Give an item to the player
        self.get_item(item_id).location = PLAYER_ID

    def dropItem(self, item_id: elements.ElemID) -> None:
        self.get_item(item_id).location = self.getLocation()
        if self.getSelectedItem() == item_id:
            self.model.player_state.selected_item_id = elements.ELEM_ID_NONE

    def hasItem(self, item_id: elements.ElemID) -> bool:
        # True if player has this item
        return self.get_item(item_id).location == PLAYER_ID

    def getItems(self) -> list[elements.ElemID]:
        # Return a list of item ids possesed by the player
        result = []
        for item_id in self.model.item_state.keys():
            if self.model.item_state[item_id].location == PLAYER_ID:
                result.append(item_id)
        return result

    def setItemLocation(self, item_id: elements.ElemID, site_id: elements.ElemID) -> None:
        # Set the location of an item
        self.get_item(item_id).location = site_id

    def getItemLocation(self, item_id: elements.ElemID) -> elements.ElemID:
        # Return the location of an item
        return self.get_item(item_id).location

    def getItemsAtLocation(self, site_id: elements.ElemID) -> list[elements.ElemID]:
        # Return list of item_ids at a specific site
        result = []
        for item_id in self.model.item_state.keys():
            if self.model.item_state[item_id].location == site_id:
                result.append(item_id)
        return result

    def increaseFriendship(self, char_id: elements.ElemID, amount: int =5) -> None:
        level = self.getFriendship(char_id) + amount
        self.model.player_state.friendship[char_id] = level

    def decreaseFriendship(self, char_id: elements.ElemID, amount: int =5) -> None:
        level = self.getFriendship(char_id) - amount
        self.model.player_state.friendship[char_id] = level

    def getFriendship(self, char_id: elements.ElemID) -> int:
        if self.model.player_state.friendship.get(char_id) is None:
            return 0
        return self.model.player_state.friendship[char_id]

    def setChatCharacter(self, char_id: elements.ElemID=elements.ELEM_ID_NONE) -> None:
        self.model.player_state.chat_who_id = char_id

    def getChatCharacter(self) -> elements.ElemID:
        """
        Returns character ID or empty string.
        """
        return self.model.player_state.chat_who_id

    def isSiteOpen(self, site_id: elements.ElemID) -> bool:
        """
        Returns True if the site is open.
        """
        return self.get_site(site_id).is_open

    def setSiteOpen(self, site_id: elements.ElemID, value: bool) -> None:
        """
        Record if site is open
        """
        self.get_site(site_id).is_open = value


def getWorldStateID(db, user_id: str, world_id: elements.WorldID) -> WorldStateID:
    """
    Get an ID for a World State record - create if needed.
    """
    now = time.time()
    c = db.cursor()
    c.execute("BEGIN EXCLUSIVE")
    c.execute(
        "SELECT id FROM world_state " + "WHERE user_id = ? and world_id = ?",
        (user_id, world_id),
    )
    r = c.fetchone()
    if r is None:
        # Insert a record and then populate
        wstate_id = WorldStateID("id%s" % os.urandom(4).hex())
        state = WorldState(wstate_id)
        logging.info("world id %s", world_id)
        c.execute(
            "INSERT INTO world_state (id, user_id, world_id, created, "
            + "updated, state) VALUES (?, ?, ?, ?, ?, ?)",
            (wstate_id, user_id, world_id, now, now, state.get_model_str()),
        )
    else:
        wstate_id = WorldStateID(r[0])
    db.commit()

    return wstate_id


def checkWorldState(db, wstate: WorldState) -> bool:
    # Ensure all characters and items are assigned.
    # Initializes everything on first load. Will also
    # set locations for newly added items and characters.

    changed = False

    characters = elements.listCharacters(db, wstate.world_id)
    sites = elements.listSites(db, wstate.world_id)
    items = elements.listItems(db, wstate.world_id)

    # Initialize sites
    avail_sites = []
    for entry in sites:
        site = elements.loadSite(db, entry.getID())
        if site is not None and not wstate.isSiteInitialized(site.getID()):
            logging.info("init site %s: open %s", site.getID(), site.getDefaultOpen())
            wstate.setSiteOpen(site.getID(), site.getDefaultOpen())
            changed = True
        if wstate.isSiteOpen(entry.getID()):
            avail_sites.append(entry)

    if len(avail_sites) > 0:
        # Assign characters to sites
        for character in characters:
            if wstate.getCharacterLocation(character.getID()) == "":
                site_entry = random.choice(avail_sites)
                wstate.setCharacterLocation(character.getID(), site_entry.getID())
                wstate.setCharacterHealth(character.getID(), 
                                          wstate.getCharacterHealth(character.getID()) - 1)
                changed = True
                logging.info(
                    "assign %s to location %s", character.getName(), site_entry.getName()
                )

        places = []
        places.extend(characters)
        places.extend(avail_sites)

        if len(characters) > 0 and len(sites) > 0:
            # Set item location - character or site
            for item_entry in items:
                if wstate.model.item_state.get(item_entry.getID()) is None:
                    changed = True
                    item = elements.loadItem(db, item_entry.getID())
                    if item is not None:
                        # Place non-mobile items at sites
                        if item.getIsMobile():
                            place = random.choice(places)
                        else:
                            place = random.choice(avail_sites)
                        wstate.setItemLocation(item.getID(), place.getID())
                        logging.info("place item %s: %s", item.getName(), place.getName())

    return changed


def loadWorldState(db, wstate_id: WorldStateID) -> WorldState:
    """
    Get or create a world state.
    """
    wstate = WorldState(WORLD_STATE_ID_NONE)
    c = db.cursor()
    c.execute(
        "SELECT user_id, world_id, state FROM world_state WHERE id = ?", (wstate_id,)
    )

    r = c.fetchone()
    if r is not None:
        wstate = WorldState(wstate_id)
        wstate.user_id = r[0]
        wstate.world_id = r[1]
        wstate.set_model_str(r[2])

        if checkWorldState(db, wstate):
            logging.info("check world state changed!")
            saveWorldState(db, wstate)

    return wstate


def saveWorldState(db, state: WorldState) -> None:
    """
    Update world state.
    """
    logging.info("world_state: save world state")
    logging.info("location: %s", state.getLocation())
    now = time.time()
    c = db.cursor()
    c.execute("BEGIN EXCLUSIVE")
    # Support changing the user_id (Still figuring that out)
    c.execute(
        "UPDATE world_state SET user_id = ?, "
        + "updated = ?, state = ? WHERE id = ?",
        (state.user_id, now, state.get_model_str(), state.wstate_id),
    )
    db.commit()

def clearWorldState(db, wstate_id: WorldStateID) -> None:
    """
    Reset an instance of world state.
    Erase all related data.
    """
    db.execute("BEGIN TRANSACTION")
    sql = "DELETE FROM info_chunks WHERE doc_id IN (SELECT id FROM info_docs WHERE wstate_id = ?)"
    db.execute(sql, (wstate_id,))
    sql = "DELETE FROM info_docs WHERE info_docs.wstate_id = ? "
    db.execute(sql, (wstate_id,))
    q = db.execute(
        "SELECT thread_id FROM character_threads WHERE world_state_id = ?", (wstate_id,)
    )
    for entry in q.fetchall():
        thread_id = entry[0]
        db.execute("DELETE FROM character_threads WHERE thread_id = ?", (thread_id,))
        db.execute("DELETE FROM threads where id = ?", (thread_id,))
    db.execute("DELETE FROM world_state where id = ?", (wstate_id,))
    db.commit()
