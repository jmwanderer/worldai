import logging
import os

import pydantic

from . import chat, design_functions, elements, threads

#
# Module for the Design Chat Session
# uses ChatSession and DesignFunctions
#


class DesignChatResponse(pydantic.BaseModel):
    chat_response: chat.ChatResponse = chat.ChatResponse(id="")
    view: dict[str, str] = dict()
    made_changes: bool = True


class DesignHistoryResponse(pydantic.BaseModel):
    history_response: chat.ChatHistoryResponse = chat.ChatHistoryResponse()
    view: dict[str, str] = dict()


class DesignChatSession:
    def __init__(self, user_id, chat_session=None):
        if chat_session is None:
            self.chatFunctions = design_functions.DesignFunctions()
            self.chat = chat.ChatSession(chatFunctions=self.chatFunctions)
        else:
            self.chatFunctions = chat_session.chatFunctions
            self.chat = chat_session
        self.user_id = user_id

    @staticmethod
    def loadChatSession(db, user_id):
        functions = design_functions.DesignFunctions()
        chat_session = chat.ChatSession(functions)
        thread = threads.get_thread(db, user_id)
        if thread is not None:
            chat_session.load(thread)
        return DesignChatSession(user_id, chat_session)

    def saveChatSession(self, db):
        thread = self.chat.save()
        threads.save_thread(db, self.user_id, thread)

    def deleteChatSession(self, db):
        threads.delete_thread(db, self.user_id)

    def chat_history(self) -> DesignHistoryResponse:
        response = DesignHistoryResponse()
        for message in self.chat.chat_history()["messages"]:
            response.history_response.messages.append(
                {
                    "id": os.urandom(4).hex(),
                    "user": message["user"],
                    "reply": message["assistant"],
                    "updates": message.get("updates", ""),
                }
            )
        response.view = self.get_view()
        response.history_response.chat_enabled = True
        return response

    def get_view(self):
        return self.chatFunctions.get_view()

    def plan_next_view(self, db) -> list[design_functions.ChatCall]:
        view = self.chatFunctions.next_view
        logging.info("plan next view %s", view.jsonStr())

        plan: list[design_functions.ChatCall] = []
        if self.chatFunctions.next_view == self.chatFunctions.current_view:
            logging.info("plan next view - no change")
            return plan
        
        if view.getType() == elements.ElementTypes.NoneType():
            self.chatFunctions.current_state = design_functions.STATE_WORLDS
            self.chatFunctions.clearCurrentView()
            logging.info("plan next view - clear view, set state to WORLDS")
            return plan

        self.chatFunctions.current_state = design_functions.STATE_WORLD
        if view.getWorldID() != self.chatFunctions.current_view.getWorldID():
            world = elements.loadWorld(db, view.getWorldID())
            if world is None:
                return plan
            chat_call =  design_functions.ChatCall()
            chat_call.tool_call = "ShowWorld"
            chat_call.system_message = f"World is '{world.getName()}'"
            logging.info("plan next view: %s", chat_call.toStr())
            plan.append(chat_call)

        if view.getID() != self.chatFunctions.current_view.getID():
            if view.getType() == elements.ElementTypes.CharacterType():
                character = elements.loadCharacter(db, view.getID())
                if character is not None:
                    chat_call =  design_functions.ChatCall()
                    chat_call.tool_call = "ShowCharacter"
                    chat_call.system_message = f"Character is '{character.getName()}'"
                    logging.info("plan next view: %s", chat_call.toStr())
                    plan.append(chat_call)

            elif view.getType() == elements.ElementTypes.ItemType():
                item = elements.loadItem(db, view.getID())
                if item is not None:
                    chat_call =  design_functions.ChatCall()
                    chat_call.tool_call = "ShowItem"
                    chat_call.system_message = f"Item is '{item.getName()}'"
                    logging.info("plan next view: %s", chat_call.toStr())
                    plan.append(chat_call)

            elif view.getType() == elements.ElementTypes.SiteType():
                site = elements.loadSite(db, view.getID())
                if site is not None:
                    chat_call =  design_functions.ChatCall()
                    chat_call.tool_call = "ShowSite"
                    chat_call.system_message = f"Site is '{site.getName()}'"
                    logging.info("plan next view: %s", chat_call.toStr())
                    plan.append(chat_call)

            elif view.getType() == elements.ElementTypes.DocumentType():
                document = elements.loadDocument(db, view.getID())
                if document is not None:
                    chat_call =  design_functions.ChatCall()
                    chat_call.tool_call = "ShowDocument"
                    chat_call.system_message = f"Document is '{document.getName()}'"
                    logging.info("plan next view: %s", chat_call.toStr())
                    plan.append(chat_call)

        return plan


    def set_view(self, db, new_view):
        # Save next view
        self.chatFunctions.set_next_view(new_view)
        view = self.chatFunctions.next_view
        logging.info("design_functions: set_view %s", view.jsonStr())

    def madeChanges(self) -> bool:
        return self.chatFunctions.madeChanges()

    def chat_start(self, db, user: str) -> DesignChatResponse:
        chat_calls = self.plan_next_view(db)
        chat_call = design_functions.ChatCall()
        chat_call.user_msg = user
        chat_calls.append(chat_call)
        self.chatFunctions.pending_chat_calls = chat_calls
        return self.chat_continue(db, "")

    def chat_continue(self, db, msg_id: str) -> DesignChatResponse:
        # This function will iterate over the entries in chatFunctions.pending_chat_Calls
        # and be called on each step of each chat call.

        # Start new message or continue existing?
        response = DesignChatResponse()
        if self.chatFunctions.message_done:
            # Start new message
            chat_call = self.chatFunctions.pending_chat_calls.pop(0)
            response.chat_response = self.chat.chat_start(db, user=chat_call.user_msg,
                                                            system=chat_call.system_message,
                                                            tool_name=chat_call.tool_call)
        else:
            # Continue in process message
            response.chat_response = self.chat.chat_continue(db, msg_id)

        response.view = self.get_view()
        response.made_changes = self.madeChanges()
        response.chat_response.chat_enabled = True

        # Note processing state
        self.chatFunctions.message_done = response.chat_response.done
        if len(self.chatFunctions.pending_chat_calls) > 0:
            # Done when message is done and no more moressages
            response.chat_response.done = False

        return response
