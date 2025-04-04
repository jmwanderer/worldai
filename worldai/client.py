"""
Standard structures for client communication.

    Jim Wanderer
    http://github.com/jmwanderer
"""


import enum
import logging
import typing

import pydantic

from . import elements, world_state


class StatusCode(str, enum.Enum):
    OK = "ok"
    ERROR = "error"


class CallStatus(pydantic.BaseModel):
    result: StatusCode = StatusCode.OK
    message: str = ""


class ElemInfo(pydantic.BaseModel):
    id: str = ""
    name: str = ""
    description: str = ""


class CharacterData(pydantic.BaseModel):
    id: str = ""
    name: str = ""
    description: str = ""
    sleeping: bool = False
    paralized: bool = False
    poisoned: bool = False
    brainwashed: bool = False
    captured: bool = False
    invisible: bool = False
    credits: int = 0
    health: int = 0
    strength: int = 0
    friendship: int = 0
    can_chat: bool = True
    inventory: list[ElemInfo] = list()


class PlayerData(pydantic.BaseModel):
    """
    Vital stats for the player character
    """

    status: CharacterData = CharacterData()
    selected_item: typing.Optional[str] = None
    # Time in minutes


# Standard message suffix for replies to client
# calls that mutate the world.  WIP
class WorldStatus(pydantic.BaseModel):
    current_time: int = 0
    game_won: bool = False
    player_alive: bool = True
    location_id: str = ""
    engaged_character_id: str = ""
    changed: bool = False
    response_message: str = ""
    last_event: str = ""
    player: PlayerData = PlayerData()


def LoadCharacterData(db, wstate, cid):
    data = CharacterData()
    character = elements.loadCharacter(db, cid)
    if character is None:
        return {"error": f"character {cid} does not exist"}

    data.name = character.getName()
    data.description = character.getDescription()
    sleeping = elements.CharStatus.SLEEPING
    data.sleeping = wstate.hasCharacterStatus(cid, sleeping)
    paralized = elements.CharStatus.PARALIZED
    data.paralized = wstate.hasCharacterStatus(cid, paralized)
    poisoned = elements.CharStatus.POISONED
    data.poisoned = wstate.hasCharacterStatus(cid, poisoned)
    brainwashed = elements.CharStatus.BRAINWASHED
    data.brainwashed = wstate.hasCharacterStatus(cid, brainwashed)
    captured = elements.CharStatus.CAPTURED
    data.captured = wstate.hasCharacterStatus(cid, captured)
    invisible = elements.CharStatus.INVISIBLE
    data.invisible = wstate.hasCharacterStatus(cid, invisible)
    data.credits = wstate.getCharacterCredits(cid)
    data.health = wstate.getCharacterHealthPercent(cid)
    data.strength = wstate.getCharacterStrengthPercent(cid)
    data.friendship = wstate.getFriendship(cid)

    for item_id in wstate.getCharacterItems(cid):
        item = elements.loadItem(db, item_id)
        if item is None:
            logging.error("unknown item in inventory: %s", item_id)
        else:
            item_info = ElemInfo()
            item_info.id = item_id
            item_info.name = item.getName()
            item_info.description = item.getDescription()
            data.inventory.append(item_info)

    # Check if character can chat with player
    if (
        data.sleeping
        or wstate.isCharacterDead(cid)
        or wstate.getCharacterLocation(cid) != wstate.getLocation()
    ):
        data.can_chat = False

    return data


def LoadPlayerData(db, wstate):
    data = PlayerData()
    data.selected_item = wstate.getSelectedItem()
    data.status.name = "Traveler"
    data.status.description = "A visitor"
    sleeping = elements.CharStatus.SLEEPING
    data.status.sleeping = wstate.hasPlayerStatus(sleeping)
    paralized = elements.CharStatus.PARALIZED
    data.status.paralized = wstate.hasPlayerStatus(paralized)
    poisoned = elements.CharStatus.POISONED
    data.status.poisoned = wstate.hasPlayerStatus(poisoned)
    brainwashed = elements.CharStatus.BRAINWASHED
    data.status.brainwashed = wstate.hasPlayerStatus(brainwashed)
    captured = elements.CharStatus.CAPTURED
    data.status.captured = wstate.hasPlayerStatus(captured)
    invisible = elements.CharStatus.INVISIBLE
    data.status.invisible = wstate.hasPlayerStatus(invisible)
    data.status.credits = wstate.getPlayerCredits()
    data.status.health = wstate.getPlayerHealthPercent()
    data.status.strength = wstate.getPlayerStrengthPercent()

    for item_id in wstate.getItems():
        item = elements.loadItem(db, item_id)
        if item is None:
            logging.error("unknown item in inventory: %s", item_id)
        else:
            item_info = ElemInfo()
            item_info.id = item_id
            item_info.name = item.getName()
            item_info.description = item.getDescription()
            data.status.inventory.append(item_info)

    return data


def update_world_status(db, wstate: world_state.WorldState, status: WorldStatus):
    status.current_time = wstate.getCurrentTime()
    status.game_won = wstate.gameWonStatus()
    status.location_id = wstate.getLocation()
    status.player_alive = wstate.getPlayerHealth() > 0
    status.engaged_character_id = wstate.getChatCharacter()
    status.player = LoadPlayerData(db, wstate)
