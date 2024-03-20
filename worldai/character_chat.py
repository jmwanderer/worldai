import os

import pydantic

from . import character_functions, chat, client, elements, threads, world_state

#
# Module for the Character Chat Session
# TODO: figure out how to format chat text in React UI
#      right now, just surpressing html.
#


class CharacterResponse(pydantic.BaseModel):
    chat_response: chat.ChatResponse = chat.ChatResponse(id="")
    world_status: client.WorldStatus = client.WorldStatus()


class CharacterHistoryResponse(pydantic.BaseModel):
    history_response: chat.ChatHistoryResponse = chat.ChatHistoryResponse()
    world_status: client.WorldStatus = client.WorldStatus()


class CharacterChat:
    def __init__(
        self,
        chat_session: chat.ChatSession,
        wstate_id,
        character_id: elements.ElemID,
        char_functions: character_functions.CharacterFunctions,
    ):
        self.chat: chat.ChatSession = chat_session
        self.wstate_id = wstate_id
        self.character_id: elements.ElemID = character_id
        self.char_functions: character_functions.CharacterFunctions = char_functions

    @staticmethod
    def loadChatSession(db, wstate_id, wid: elements.WorldID, cid: elements.ElemID):
        functions = character_functions.CharacterFunctions(wstate_id, wid, cid)
        chat_session = chat.ChatSession(chatFunctions=functions)
        thread = threads.get_character_thread(db, wstate_id, cid)
        if thread is not None:
            chat_session.load(thread)
        return CharacterChat(chat_session, wstate_id, cid, functions)

    def saveChatSession(self, db):
        thread = self.chat.save()
        threads.save_character_thread(db, self.wstate_id, self.character_id, thread)

    def deleteChatSession(self, db):
        threads.delete_character_thread(db, self.wstate_id, self.character_id)

    def chat_history(self, db) -> CharacterHistoryResponse:
        response = CharacterHistoryResponse()
        for message in self.chat.chat_history()["messages"]:
            response.history_response.messages.append(
                {
                    "id": os.urandom(4).hex(),
                    "user": message["user"],
                    "reply": message["assistant"],
                    "event": message["system"],
                    "updates": message.get("updates", ""),
                }
            )
        wstate = world_state.loadWorldState(db, self.wstate_id)
        client.update_world_status(db, wstate, response.world_status)
        return response

    def checkChatEnabled(self, wstate: world_state.WorldState) -> bool:
        cid = wstate.getChatCharacter()
        if cid is None:
            return False
        # Check player and character are in the same location
        chat_enabled = wstate.getCharacterLocation(cid) == wstate.getLocation()
        # Check player and character are alive
        chat_enabled = chat_enabled and wstate.getCharacterHealth(cid) > 0
        chat_enabled = chat_enabled and not wstate.hasCharacterStatus(cid, elements.CharStatus.SLEEPING)
        chat_enabled = chat_enabled and wstate.getPlayerHealth() > 0
        return chat_enabled

    def chat_start(self, db, user: str) -> CharacterResponse:
        if len(user) == 0:
            message = None
        else:
            message = user

        # Load any pending character events into a system message
        wstate = world_state.loadWorldState(db, self.wstate_id)
        events = wstate.getCharacterEvents(self.character_id)
        system_message = None
        if len(events) > 0:
            system_message = "\n".join(events)
            # Only save if there were events removed, otherwise it is not necessary
            world_state.saveWorldState(db, wstate)
            character = elements.loadCharacter(db, self.character_id)
            if character  is not None:
                system_message = system_message.format(name=character.getName())

        response = CharacterResponse()
        response.chat_response = self.chat.chat_start(db, user=message, 
                                                      system=system_message,
                                                      respond_to_system=True)

        # Reload world state as it may have changed during message processing
        wstate = world_state.loadWorldState(db, self.wstate_id)
        wstate.advanceTime(1)
        world_state.saveWorldState(db, wstate)

        response.chat_response.chat_enabled = self.checkChatEnabled(wstate)
        client.update_world_status(db, wstate, response.world_status)
        response.world_status.changed = self.char_functions.world_changed
        return response

    def chat_continue(self, db, msg_id: str) -> CharacterResponse:
        response = CharacterResponse()
        response.chat_response = self.chat.chat_continue(db, msg_id)
        wstate = world_state.loadWorldState(db, self.wstate_id)
        response.chat_response.chat_enabled = self.checkChatEnabled(wstate)
        client.update_world_status(db, wstate, response.world_status)
        response.world_status.changed = self.char_functions.world_changed
        return response

    def chat_event_start(self, db, event: str) -> CharacterResponse:
        response = CharacterResponse()

        # Load any pending character events into a system message
        wstate = world_state.loadWorldState(db, self.wstate_id)
        events = wstate.getCharacterEvents(self.character_id)
        if len(events) > 0:
            world_state.saveWorldState(db, wstate)

        if len(event) > 0:
            events.append(event)

        if len(events) > 0:
            system = "\n".join(events)
            character = elements.loadCharacter(db, self.character_id)
            if character  is not None:
                system = system.format(name=character.getName())

            response.chat_response = self.chat.chat_start(db, system=system,
                                                          respond_to_system=True)

        wstate = world_state.loadWorldState(db, self.wstate_id)
        response.chat_response.chat_enabled = self.checkChatEnabled(wstate)
        client.update_world_status(db, wstate, response.world_status)
        response.world_status.changed = self.char_functions.world_changed
        return response
