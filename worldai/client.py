"""
Standard structures for client communication.
"""

import enum
import pydantic
import logging

from . import world_state

class StatusCode(str, enum.Enum):
    OK = "ok"
    ERROR = "error"

class CallStatus(pydantic.BaseModel):
    result: StatusCode = StatusCode.OK
    message: str = ""

# Standard message suffix for replies to client
# calls that mutate the world.  WIP
class WorldStatus(pydantic.BaseModel):
    current_time: int = 0
    player_alive: bool = True
    location_id: str = ""
    engaged_character_id: str = ""
    changed: bool = False
    response_message: str = ""
    last_event: str = ""


def update_world_status(wstate: world_state.WorldState, status: WorldStatus):
    status.current_time = wstate.getCurrentTime()
    status.location_id = wstate.getLocation()
    status.player_alive = wstate.getPlayerHealth() > 0
    status.engaged_character_id = wstate.getChatCharacter()
