"""
Standard structures for client communication.
"""

import enum
import pydantic

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
    changed: bool = False
    response_message: str = ""

