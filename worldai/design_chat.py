import io
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
  def __init__(self, chat_session=None):
    if chat_session is None:
      self.chatFunctions = design_functions.DesignFunctions()
      self.chat = chat.ChatSession(chatFunctions=self.chatFunctions)
    else:
      self.chatFunctions = chat_session.chatFunctions
      self.chat = chat_session


  def loadChatSession(db, session_id):
    functions = design_functions.DesignFunctions()
    chat_session = chat.ChatSession(session_id, functions)    
    thread = threads.get_thread(db, session_id)
    if thread is not None:
      f = io.BytesIO(thread)
      chat_session.load(f)
      f.close()
    return DesignChatSession(chat_session)

  def saveChatSession(self, db):
    f = io.BytesIO()
    self.chat.save(f)
    thread = f.getvalue()
    threads.save_thread(db, self.chat.id, thread)
    f.close()

  def deleteChatSession(self, db):
    threads.delete_thread(db, self.chat.id)    

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

  def set_view(self, view):
    logging.info("design chat set view")
    self.chatFunctions.set_view(view)

  def madeChanges(self):
    return self.chatFunctions.madeChanges()

  def chat_message(self, db, user):
    # Handle changing the view
    if self.chatFunctions.next_view != self.chatFunctions.current_view:
      logging.info("*** Change view")
      # TODO: handle failure
      next_view = self.chatFunctions.next_view
      current_view = self.chatFunctions.current_view
            
      # Handle when next view is world list.
      if next_view.getType() == elements.ElementType.NoneType():
        self.chatFunctions.current_state = design_functions.STATE_WORLDS
        self.chatFunctions.clearCurrentView()

      # Handle a change in the current world.
      if next_view.getWorldID() != current_view.getWorldID():
        world = elements.loadWorld(db, next_view.getWorldID())
        message = "Show world '%s'" % world.getName()
        self.chatFunctions.current_state = design_functions.STATE_WORLDS
        self.chat.chat_exchange(db, message)

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
        message = None
        if next_view.getType() == elements.ElementType.CharacterType():
          character = elements.loadCharacter(db, next_view.getID())
          message = "Show character '%s'" % character.getName()          

        elif next_view.getType() == elements.ElementType.ItemType():
          item = elements.loadItem(db, next_view.getID())
          message = "Show item '%s'" % item.getName()

        elif next_view.getType() == elements.ElementType.SiteType():
          site = elements.loadSite(db, next_view.getID())
          message = "Show site '%s'" % site.getName()

        self.chatFunctions.current_state = new_state
        if message is not None:
          self.chat.chat_exchange(db, message)


    return self.chat.chat_exchange(db, user)

    
