import io

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
    return self.chat.chat_history()

  def get_view(self):
    return self.chatFunctions.get_view()

  def set_view(self, view):
    self.chatFunctions.set_view(view)

  def madeChanges(self):
    return self.chatFunctions.madeChanges()

  def chat_message(self, db, user):
    if not self.chatFunctions.next_view.noElement():
      # TODO: handle failure
      next_view = self.chatFunctions.next_view
      current_view = self.chatFunctions.current_view
      
      if next_view.getWorldID() != current_view.getWorldID():
        world = elements.loadWorld(db, next_view.getWorldID())
        message = "Read world '%s'" % world.getName()
        self.chat.chat_exchange(db, message)

      # Refresh current_view, may have changed
      current_view = self.chatFunctions.current_view
      new_state = design_functions.elemTypeToState(next_view.getType())
        
      if next_view.getID() != current_view.getID():
        message = None
        if next_view.getType() == elements.ElementType.CharacterType():
          character = elements.loadCharacter(db, next_view.getID())
          message = "Read character '%s'" % character.getName()          

        elif next_view.getType() == elements.ElementType.ItemType():
          item = elements.loadItem(db, next_view.getID())
          message = "Read item '%s'" % item.getName()

        elif next_view.getType() == elements.ElementType.SiteType():
          site = elements.loadSite(db, next_view.getID())
          message = "Read site '%s'" % site.getName()

        self.chatFunctions.current_state = new_state
        if message is not None:
          self.chat.chat_exchange(db, message)
      self.chatFunctions.next_view = elements.ElemTag()

    return self.chat.chat_exchange(db, user)

    
