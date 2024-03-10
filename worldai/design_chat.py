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
    def __init__(self, session_id, chat_session=None):
        if chat_session is None:
            self.chatFunctions = design_functions.DesignFunctions()
            self.chat = chat.ChatSession(chatFunctions=self.chatFunctions)
        else:
            self.chatFunctions = chat_session.chatFunctions
            self.chat = chat_session
        self.session_id = session_id

    @staticmethod
    def loadChatSession(db, session_id):
        functions = design_functions.DesignFunctions()
        chat_session = chat.ChatSession(functions)
        thread = threads.get_thread(db, session_id)
        if thread is not None:
            chat_session.load(thread)
        return DesignChatSession(session_id, chat_session)

    def saveChatSession(self, db):
        thread = self.chat.save()
        threads.save_thread(db, self.session_id, thread)

    def deleteChatSession(self, db):
        threads.delete_thread(db, self.session_id)

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

    def plan_next_view(self, db):
        view = self.chatFunctions.next_view
        logging.info("plan next view %s", view.jsonStr())

        plan = []
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
            entry = ("ShowWorld", f"World id is '{world.getName()}'")
            logging.info("plan next view: %s, %s", entry[0], entry[1])
            plan.append(entry)

        if view.getID() != self.chatFunctions.current_view.getID():
            if view.getType() == elements.ElementTypes.CharacterType():
                character = elements.loadCharacter(db, view.getID())
                if character is not None:
                    entry = ("ShowCharacter",  f"Character is '{character.getName()}'")
                    logging.info("plan next view: %s, %s", entry[0], entry[1])
                    plan.append(entry)

            elif view.getType() == elements.ElementTypes.ItemType():
                item = elements.loadItem(db, view.getID())
                if item is not None:
                    entry = ("ShowItem", f"Item is '{item.getName()}'")
                    logging.info("plan next view: %s, %s", entry[0], entry[1])
                    plan.append(entry)

            elif view.getType() == elements.ElementTypes.SiteType():
                site = elements.loadSite(db, view.getID())
                if site is not None:
                    entry = ("ShowSite", f"Site is '{site.getName()}'")
                    logging.info("plan next view: %s, %s", entry[0], entry[1])
                    plan.append(entry)

            elif view.getType() == elements.ElementTypes.DocumentType():
                document = elements.loadDocument(db, view.getID())
                if document is not None:
                    entry = ("ShowDocument", f"Document is '{document.getName()}'")
                    logging.info("plan next view: %s, %s", entry[0], entry[1])
                    plan.append(entry)

        return plan


    def set_view(self, db, new_view):
        # Save next view
        self.chatFunctions.set_next_view(new_view)
        view = self.chatFunctions.next_view
        logging.info("design_functions: set_view %s", view.jsonStr())

    def madeChanges(self) -> bool:
        return self.chatFunctions.madeChanges()

    def chat_start(self, db, user: str) -> DesignChatResponse:
        plan = self.plan_next_view(db)
        for (tool, msg) in plan:
            logging.info("chat run %s", tool)
            self.chat.chat_exchange(
                db, system=msg, tool_choice=tool, call_limit=1
            )
            logging.info("done - current view: %s", self.chatFunctions.current_view.jsonStr())

        response = DesignChatResponse()
        response.chat_response = self.chat.chat_start(db, user=user)
        response.view = self.get_view()
        response.made_changes = self.madeChanges()
        response.chat_response.chat_enabled = True
        return response

    def chat_continue(self, db, msg_id: str) -> DesignChatResponse:
        response = DesignChatResponse()
        response.chat_response = self.chat.chat_continue(db, msg_id)
        response.view = self.get_view()
        response.made_changes = self.madeChanges()
        response.chat_response.chat_enabled = True
        return response
