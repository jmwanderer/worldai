from . import chat
from . import elements
from . import threads
from . import character_functions

import os

"""
Module for the Character Chat Session
TODO: figure out how to format chat text in React UI
      right now, just surpressing html. 
"""

class CharacterChat:
  def __init__(self, chat_session, wstate_id, character_id):
    self.chat = chat_session
    self.wstate_id = wstate_id
    self.character_id = character_id

  def loadChatSession(db, wstate_id, wid, cid):
    functions = character_functions.CharacterFunctions(wstate_id, wid, cid)     
    chat_session = chat.ChatSession(chatFunctions=functions)
    thread = threads.get_character_thread(db, wstate_id, cid)
    if thread is not None:
      chat_session.load(thread)
    return CharacterChat(chat_session, wstate_id, cid)

  def saveChatSession(self, db):
    thread = self.chat.save()
    threads.save_character_thread(db,
                                  self.wstate_id,
                                  self.character_id,
                                  thread)

  def deleteChatSession(self, db):
    threads.delete_character_thread(db,
                                   self.wstate_id,
                                   self.character_id)
    

  def chat_history(self):
    history = []
    for message in self.chat.chat_history()["messages"]:
      history.append({ "id": os.urandom(4).hex(),
                       "user": message["user"],
                       "reply": message["assistant"],
                       "event": message["system"],
                       "updates": message.get("updates", "")
                      })
    return history

  def chat_message(self, db, user):
    if len(user) == 0:
      user = None
    return self.chat.chat_exchange(db, user=user)

  def chat_start(self, db, user):
    if len(user) == 0:
      user = None
    return self.chat.chat_start(db, user=user)

  def chat_continue(self, db, msg_id):
    return self.chat.chat_continue(db, msg_id)

  def chat_event(self, db, event):
    return self.chat.chat_exchange(db, system=event)
        


    
