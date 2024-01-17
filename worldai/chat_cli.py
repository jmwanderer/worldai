import os
import logging
import openai

from . import chat
from . import design_chat
from . import chat_functions
from . import design_functions
from . import db_access

def get_user_input():
  return input("> ").strip()

def chat_loop():
  db = db_access.open_db()
  chat_session = design_chat.DesignChatSession()
  logging.info("\nstartup*****************");
  print("Welcome to the world builder!\n")
  print("You can create and design worlds with main characters, key sites, and special items.")
  print("")

  while True:
    try:
      user = get_user_input()
    except EOFError:
      break
    if user == 'exit':
      break
    if len(user) == 0:
      continue

    message = chat_session.chat_message(db, user)
    assistant_message = message["assistant"]
    text = message.get("updates")
    print(assistant_message)
    if len(text) > 0:
      print(text)

  #pretty_print_conversation(BuildMessages(message_history))
  print("Tokens")
  
  print("\nRunning total")
  chat_functions.dump_token_usage(db)
  db.close()

