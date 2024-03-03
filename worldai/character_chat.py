import os
import pydantic

from . import character_functions, chat, threads, client, world_state, elements

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
    def __init__(self, chat_session: chat.ChatSession, wstate_id, 
                 character_id: elements.ElemID, char_functions: character_functions.CharacterFunctions):
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
        # Check player and character are in the same location
        chat_enabled = wstate.getCharacterLocation(cid) == wstate.getLocation()
        # Check player and character are alive
        chat_enabled = chat_enabled and wstate.getCharacterHealth(cid) > 0
        chat_enabled = chat_enabled and wstate.getPlayerHealth() > 0
        return chat_enabled

    def chat_message(self, db, user: str) -> CharacterResponse:
        if len(user) == 0:
            message = None
        else:
            message = user
        response = CharacterResponse() 
        response.chat_response = self.chat.chat_exchange(db, user=message)
        wstate = world_state.loadWorldState(db, self.wstate_id)
        response.chat_response.chat_enabled = self.checkChatEnabled(wstate) 
        client.update_world_status(db, wstate, response.world_status)
        response.world_status.changed = self.char_functions.world_changed
        return response

    def chat_start(self, db, user: str) -> CharacterResponse:
        if len(user) == 0:
            message = None
        else:
            message = user
        response = CharacterResponse() 
        response.chat_response = self.chat.chat_start(db, user=message)
        wstate = world_state.loadWorldState(db, self.wstate_id)
        wstate.advanceTime(1)
        world_state.saveWorldState(db, wstate)
        response.chat_response.chat_enabled = self.checkChatEnabled(wstate) 
        client.update_world_status(db, wstate, response.world_status)
        response.world_status.changed = self.char_functions.world_changed
        return response


    def chat_continue(self, db, msg_id: str) -> CharacterResponse:
        response = CharacterResponse() 
        response.chat_response =  self.chat.chat_continue(db, msg_id)
        wstate = world_state.loadWorldState(db, self.wstate_id)
        response.chat_response.chat_enabled = self.checkChatEnabled(wstate) 
        client.update_world_status(db, wstate, response.world_status)
        response.world_status.changed = self.char_functions.world_changed
        return response

    def chat_event(self, db, event: str) -> CharacterResponse:
        response = CharacterResponse() 
        if len(event) > 0:
            response.chat_response =  self.chat.chat_exchange(db, system=event)
        wstate = world_state.loadWorldState(db, self.wstate_id)
        response.chat_response.chat_enabled = self.checkChatEnabled(wstate) 
        client.update_world_status(db, wstate, response.world_status)
        response.world_status.changed = self.char_functions.world_changed
        return response
