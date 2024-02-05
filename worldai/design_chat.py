import os
import logging

from . import chat
from . import elements
from . import design_functions
from . import threads

"""
Module for the Design Chat Session
- uses ChatSession and DesignFunctions
"""

class DesignChatSession:
  def __init__(self, session_id, chat_session=None):
    if chat_session is None:
      self.chatFunctions = design_functions.DesignFunctions()
      self.chat = chat.ChatSession(chatFunctions=self.chatFunctions)
    else:
      self.chatFunctions = chat_session.chatFunctions
      self.chat = chat_session
    self.session_id = session_id


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

  def chat_history(self):
    history = []
    for message in self.chat.chat_history()["messages"]:
      history.append({ "id": os.urandom(4).hex(),
                       "user": message["user"],
                       "reply": message["assistant"],
                       "updates": message.get("updates", "")
                      })
    return history

  def get_view(self):
    return self.chatFunctions.get_view()

  def set_view(self, db, view):
    logging.info("design chat set view")
    self.chatFunctions.set_view(view)

    if self.chatFunctions.next_view != self.chatFunctions.current_view:
      logging.info("*** Change view")
      # TODO: handle failure
      next_view = self.chatFunctions.next_view
      current_view = self.chatFunctions.current_view
      logging.info("current view: %s", current_view.jsonStr())
      logging.info("next view: %s", next_view.jsonStr())      
            
      # Handle when next view is world list.
      if next_view.getType() == elements.ElementType.NoneType():
        self.chatFunctions.current_state = design_functions.STATE_WORLDS
        self.chatFunctions.clearCurrentView()
        return

      # Handle a change in the current world.
      if next_view.getWorldID() != current_view.getWorldID():
        logging.info("Show world '%s'", next_view.getWorldID())
        self.chatFunctions.current_state = design_functions.STATE_WORLDS
        load_id = next_view.getWorldID()
        self.chat.chat_exchange(db, system=f"World id is '{load_id}'",
                                tool_choice="ShowWorld",
                                call_limit=1)

      # Handle when next view is world.
      if next_view.getType() == elements.ElementType.WorldType():
        new_state = design_functions.elemTypeToState(next_view.getType())
        logging.info("world view, change state to: %s", new_state)
        self.chatFunctions.current_state = new_state        
        self.chatFunctions.current_view = next_view

      # Refresh current_view, may have changed
      current_view = self.chatFunctions.current_view
      new_state = design_functions.elemTypeToState(next_view.getType())

      # Handle if the next view is a new item, character, or site
      if next_view.getID() != current_view.getID():
        tool_choice = None
        load_id = next_view.getID()        
        if next_view.getType() == elements.ElementType.CharacterType():
          character = elements.loadCharacter(db, next_view.getID())
          logging.info("Show character '%s'", character.getName())
          tool_choice = "ShowCharacter"
          system=f"Character id is '{load_id}'"

        elif next_view.getType() == elements.ElementType.ItemType():
          item = elements.loadItem(db, next_view.getID())
          logging.info("Show item '%s'", item.getName())
          tool_choice = "ShowItem"
          system=f"Item id is '{load_id}'"          

        elif next_view.getType() == elements.ElementType.SiteType():
          site = elements.loadSite(db, next_view.getID())
          logging.info("Show site '%s'", site.getName())
          tool_choice = "ShowSite"
          system=f"Site id is '{load_id}'"                    

        self.chatFunctions.current_state = new_state
        if tool_choice is not None:
          self.chat.chat_exchange(db, system=system,
                                  tool_choice=tool_choice,
                                  call_limit=1)

    

  def madeChanges(self):
    return self.chatFunctions.madeChanges()

  def chat_start(self, db, user):
    return self.chat.chat_start(db, user=user)
  
  def chat_continue(self, db, msg_id):
    return self.chat.chat_continue(db, msg_id)
  
    
