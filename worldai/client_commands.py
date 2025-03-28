"""
Support game play commands send from the client

    Jim Wanderer
    http://github.com/jmwanderer
"""


"""
Implements the game play commands.
"""

import enum
import logging
import typing

import pydantic

from . import client, elements, world_state


class CommandName(str, enum.Enum):
    go = "go"
    take = "take"
    drop = "drop"
    select = "select"
    use = "use"
    engage = "engage"
    disengage = "disengage"


class Command(pydantic.BaseModel):
    """
    Represents state for a instance of a character
    Either a player or an NPC
    """

    name: CommandName
    to: typing.Optional[str] = None
    item: typing.Optional[str] = None
    character: typing.Optional[str] = None


class CommandResponse(pydantic.BaseModel):
    """
    Response to a client command
    """

    call_status: client.CallStatus = (
        client.CallStatus()
    )  # ok or error with an optional message  (message not currently used...)
    # World status has:
    # response_message - Return message in response to command. E.G. Nothing happened.
    # changed - indicates if the state of the world was changed
    world_status: client.WorldStatus = client.WorldStatus()


class ClientActions:
    def __init__(self, db, world: elements.World, wstate: world_state.WorldState, player_name: str):
        self.db = db
        self.world = world
        self.wstate  = wstate
        self.player_name = player_name

    def ExecCommand(self, command):
        """
        Implement a command from the client.
        Return a json result for the client
        """
        response = CommandResponse()

        if command.name == CommandName.go:
            site_id = command.to
            # Verify location
            site = elements.loadSite(self.db, site_id)
            if site is not None:
                logging.info(
                    "go site %s, open = %s", site_id, self.wstate.isSiteOpen(site_id)
                )

                if self.wstate.isSiteOpen(site_id):
                    self.wstate.setLocation(site_id)
                    logging.info("GO: set location %s", site_id)
                    response.world_status.response_message = (
                        f"Arrival: {site.getName()}"
                    )
                    self.wstate.advanceTime(30)
                else:
                    response.world_status.response_message = (
                        f"{site.getName()} is not open"
                    )
            else:
                self.wstate.setLocation("")
                logging.info("GO: clear location")
            response.world_status.changed = True

        elif command.name == CommandName.take:
            item_id = command.item
            logging.info("take item %s", item_id)
            item = elements.loadItem(self.db, item_id)
            if item is None:
                response.call_status.result = client.StatusCode.ERROR
            # Verify
            elif self.wstate.getItemLocation(item_id) == self.wstate.getLocation():
                if item.getIsMobile():
                    self.wstate.addItem(item_id)
                    response.world_status.changed = True
                    response.world_status.response_message = (
                        f"You picked up {item.getName()}"
                    )

        elif command.name == CommandName.drop:
            item_id = command.item
            logging.info("drop item %s", item_id)
            item = elements.loadItem(self.db, item_id)
            if item is None:
                response.call_status.result = client.StatusCode.ERROR
            else:
                response.world_status = self.DropItem(item)
            if command.character is not None:
                if elements.loadCharacter(self.db, command.character) is not None:
                    self.wstate.addCharacterEvent(
                        command.character, 
                        response.world_status.last_event)

        elif command.name == CommandName.select:
            item_id = command.item
            if item_id is None or len(item_id) == 0:
                self.wstate.selectItem(elements.ELEM_ID_NONE)
                response.world_status.changed = True
            else:
                logging.info("select item %s", item_id)
                if self.wstate.hasItem(item_id):
                    item = elements.loadItem(self.db, item_id)
                    self.wstate.selectItem(item_id)
                    response.world_status.changed = True
                    response.world_status.response_message = (
                        f"You are holding {item.getName()}"
                    )

        elif command.name == CommandName.use:
            item = elements.loadItem(self.db, command.item)
            if item is None:
                response.call_status.result = client.StatusCode.ERROR
            else:
                logging.info("use item %s", command.item)
                response.world_status = self.UseItem(item)
                if response.world_status.changed:
                    self.wstate.advanceTime(5)

        elif command.name == CommandName.engage:
            character_id = command.character
            character = elements.loadCharacter(self.db, character_id)
            if character is None:
                response.call_status.result = client.StatusCode.ERROR

            elif self.wstate.getLocation() != self.wstate.getCharacterLocation(
                character_id
            ):
                # Check same location
                response.world_status.response_message = (
                    f"{character.getName()} is not here"
                )
            else:
                self.wstate.setChatCharacter(character_id)
                logging.info("engage character %s", character_id)
                logging.info("ENGAGE: location: %s", self.wstate.getLocation())
                response.world_status.changed = True
                if not self.wstate.isCharacterDead(character_id):
                    response.world_status.response_message = (
                        f"Talking to {character.getName()}"
                    )
                else:
                    response.world_status.response_message = (
                        f"{character.getName()} is dead"
                    )

        elif command.name == CommandName.disengage:
            self.wstate.setChatCharacter(elements.ELEM_ID_NONE)
            logging.info("disengage character")
            response.world_status.changed = True
            response.world_status.response_message = f"Talking to nobody"

        # Check if end conditions completed
        if  response.world_status.changed:
            response.world_status.game_won = self.wstate.checkEndConditions(self.world)

        client.update_world_status(self.db, self.wstate, response.world_status)
        logging.info("Client command response: %s", response.model_dump())
        return response

    def DropItem(self, item: elements.Item) -> client.WorldStatus:
        """
        Player drops an item.
        Sets a status message and an event in case it is needed.
        """
        world_status = client.WorldStatus()
        if self.wstate.hasItem(item.getID()):
            self.wstate.dropItem(item.getID())
            world_status.changed = True
            world_status.response_message = (
                f"You dropped {item.getName()}"
            )
            world_status.last_event = f"{self.player_name} dropped {item.getName()}"
        client.update_world_status(self.db, self.wstate, world_status)
        return world_status

    def UseItemCharacter(
        self, item: elements.Item, character: elements.Character
    ) -> client.WorldStatus:
        """
        Player uses an item in the context of a specific character
        Returns a client.WorldStatus with the following set:
        - changed - did the world state change?
        - last_event - event to feed to the chat thread for the character
        - response_message - status message for the user
        """
        # TODO: check character is engaged, same location

        logging.info("use character %s item %s", character.getID(), item.getID())
        world_status = self.UseItem(item, character)
        if world_status.changed:
            self.wstate.advanceTime(5)
        client.update_world_status(self.db, self.wstate, world_status)
        return world_status

    def UseItem(self, item, character=None):
        """
         Returns a client.WorldStatus with the following set:
        - changed - did the world state change?
        - last_event - event to feed to the chat thread for the character, if any
        - response_message - status message for the user
        does NOT call client.update_world_status to set location, etc. Caller will do this.
        """
        logging.info("Use item %s", item.getName())
        cid = elements.ELEM_ID_NONE
        world_status = client.WorldStatus()
        if character != None:
            cid = character.getID()

        if item.getIsMobile():
            # Verify user has the item
            if not self.wstate.hasItem(item.getID()):
                logging.info(
                    "item %s is mobile, but user does not possess", item.getName()
                )
                world_status.response_message = f"You don't have {item.getName()}"
                return world_status
        else:
            # Verify same location
            if self.wstate.getItemLocation(item.getID()) != self.wstate.getLocation():
                logging.info(
                    "item %s is not mobile and not in same location", item.getName()
                )
                world_status.response_message = f"{item.getName()} is not present"
                return world_status

        sleeping = elements.CharStatus.SLEEPING
        poisoned = elements.CharStatus.POISONED
        paralized = elements.CharStatus.PARALIZED
        brainwashed = elements.CharStatus.BRAINWASHED
        captured = elements.CharStatus.CAPTURED
        invisible = elements.CharStatus.INVISIBLE
        logging.info("use item - %s", item.getAbility().effect)

        # Apply an effect
        world_status.response_message = "Nothing happened"
        match item.getAbility().effect:
            case elements.ItemEffect.HEAL:
                # Self or other
                if cid == elements.ELEM_ID_NONE:
                    if not self.wstate.isPlayerHealthy():
                        world_status.response_message = "You are healed"
                        self.wstate.healPlayer()
                    else:
                        world_status.response_message = "You are already heathly"
                else:
                    if not self.wstate.isCharacterDead(cid):
                        if not self.wstate.isCharacterHealthy(cid):
                            self.wstate.healCharacter(cid)
                            world_status.response_message = (
                                f"{character.getName()} is healed"
                            )
                            world_status.last_event = f"{self.player_name} uses {item.getName()} to heal {character.getName()}"
                        else:
                            world_status.response_message = (
                                f"{character.getName()} is already healthy"
                            )
                            world_status.last_event = f"{self.player_name} uses {item.getName()} to heal {character.getName()}, but they were already healthy"

            case elements.ItemEffect.HURT:
                # Only other TODO: extend so characters can use
                if cid != elements.ELEM_ID_NONE:
                    health = self.wstate.getCharacterHealth(cid) - 4
                    health = max(health, 0)
                    self.wstate.setCharacterHealth(cid, health)
                    if self.wstate.isCharacterDead(cid):
                        world_status.response_message = f"{character.getName()} is dead"
                        world_status.last_event = (
                            f"{self.player_name} uses {item.getName()} to kill {character.getName()}. "
                            + world_status.response_message
                        )
                    else:
                        world_status.response_message = (
                            f"{character.getName()} took damage"
                        )
                        world_status.last_event = f"{self.player_name} uses {item.getName()} to cause {character.getName()} harm"

            case elements.ItemEffect.PARALIZE:
                # Only other TODO: extend so characters can use
                if cid != elements.ELEM_ID_NONE:
                    self.wstate.addCharacterStatus(cid, paralized)
                    world_status.response_message = (
                        f"{character.getName()} is paralized"
                    )
                    world_status.last_event = (
                        f"{self.player_name} uses {item.getName()} to paralize {character.getName()}.\n" +
                        f"{character.getName()} is paralized."
                    )


            case elements.ItemEffect.POISON:
                # Other
                if cid != elements.ELEM_ID_NONE:
                    self.wstate.addCharacterStatus(cid, poisoned)
                    world_status.response_message = f"{character.getName()} is poisoned"
                    world_status.last_event = (
                        f"{self.player_name} uses {item.getName()} to poison {character.getName()}"
                    )

            case elements.ItemEffect.SLEEP:
                # Other character
                if cid != elements.ELEM_ID_NONE:
                    if not self.wstate.hasCharacterStatus(cid, sleeping):
                        # Sleep character
                        self.wstate.addCharacterStatus(cid, sleeping)
                        world_status.response_message = f"{character.getName()} is sleeping"
                        world_status.last_event = (
                            f"{self.player_name} uses {item.getName()} to put {character.getName()} to sleep.\n"  +
                            f"{character.getName()} is asleep."
                        )
                    else:
                        # Wake character
                        self.wstate.removeCharacterStatus(cid, sleeping)
                        world_status.response_message = f"{character.getName()} is awake"
                        world_status.last_event = (
                            f"{self.player_name} uses {item.getName()} to wake {character.getName()}.\n"  +
                            f"{character.getName()} is awake."
                        )

            case elements.ItemEffect.BRAINWASH:
                # Other character
                if cid != elements.ELEM_ID_NONE:
                    self.wstate.addCharacterStatus(cid, brainwashed)
                    world_status.response_message = (
                        f"{character.getName()} is brainwashed"
                    )

            case elements.ItemEffect.CAPTURE:
                # Other character - toggle
                if cid != elements.ELEM_ID_NONE:
                    if self.wstate.hasCharacterStatus(cid, captured):
                        self.wstate.removeCharacterStatus(cid, captured)
                        world_status.response_message = (
                            f"{character.getName()} is released"
                        )
                        world_status.last_event = f"{self.player_name} uses {item.getName()} to release {character.getName()} from capture"
                    else:
                        self.wstate.addCharacterStatus(cid, captured)
                        world_status.response_message = (
                            f"{character.getName()} is captured"
                        )
                        world_status.last_event = f"{self.player_name} uses {item.getName()} to capture {character.getName()}"

            case elements.ItemEffect.INVISIBILITY:
                # Self only - toggle
                if self.wstate.hasPlayerStatus(invisible):
                    self.wstate.removePlayerStatus(invisible)
                    world_status.response_message = "You are now visible"
                    world_status.last_event = f"{self.player_name} has become visible"
                else:
                    self.wstate.addPlayerStatus(invisible)
                    world_status.response_message = "You are invisible"
                    world_status.last_event = (
                        f"{self.player_name} uses {item.getName()} to turn invisible"
                    )

            case elements.ItemEffect.OPEN:
                site_id = item.getAbility().site_id

                site = elements.loadSite(self.db, site_id)
                if site != elements.ELEM_ID_NONE:
                    if not self.wstate.isSiteOpen(site_id):
                        self.wstate.setSiteOpen(site_id, True)
                        world_status.response_message = (
                            f"Site {site.getName()} is now open."
                        )
                    else:
                        world_status.response_message = (
                            f"Site {site.getName()} is already open."
                        )
        world_status.changed = True
        return world_status
