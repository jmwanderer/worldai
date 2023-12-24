from . import chat
from . import elements
from . import threads
from . import character_functions

import io
import os

"""
Module for the Character Chat Session
"""

class CharacterChat:
  def __init__(self, chat_session, world_id, character_id):
    self.chat = chat_session
    self.world_id = world_id
    self.character_id = character_id

  def loadChatSession(db, session_id, wid, cid):
    functions = character_functions.CharacterFunctions(wid, cid)     
    chat_session = chat.ChatSession(id=session_id,
                                    chatFunctions=functions)
    thread = threads.get_character_thread(db, session_id, wid, cid)
    if thread is not None:
      f = io.BytesIO(thread)
      chat_session.load(f)
      f.close()
    return CharacterChat(chat_session, wid, cid)

  def saveChatSession(self, db):
    f = io.BytesIO()
    self.chat.save(f)
    thread = f.getvalue()
    threads.save_character_thread(db,
                                  self.chat.id,
                                  self.world_id,
                                  self.character_id,
                                  thread)
    f.close()

  def deleteChatSession(self, db):
    threads.delete_character_thread(db,
                                   self.chat.id,
                                   self.world_id,
                                   self.character_id)
    

  def chat_history(self):
    history = []
    for message in self.chat.chat_history(to_html=False)["messages"]:
      history.append({ "id": os.urandom(4).hex(),
                       "user": message["user"],
                       "reply": message["assistant"]
                      })
    return history

  def chat_message(self, db, user):
    return self.chat.chat_exchange(db, user)    
        


    
