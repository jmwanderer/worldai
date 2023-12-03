#!/usr/bin/env python3
"""
Text chat client that can make function calls update world model

From: https://cookbook.openai.com/examples/how_to_call_functions_with_chat_models
"""

import os
import json
import logging
import openai
import requests
import pickle

from tenacity import retry, wait_random_exponential, stop_after_attempt
from termcolor import colored
import tiktoken

from . import db_access
from . import elements
from . import chat_functions

GPT_MODEL = "gpt-3.5-turbo-1106"
# Can be higher, but save $$$ with some potential loss in perf
MESSAGE_THRESHOLD=3_000


@retry(wait=wait_random_exponential(multiplier=1, max=40),
       stop=stop_after_attempt(3))
def chat_completion_request(messages, tools=None, model=GPT_MODEL):
  headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + openai.api_key,
  }
  json_data = {"model": model, "messages": messages}
  if tools is not None:
    json_data.update({"tools": tools})
  try:
    response = requests.post(
      "https://api.openai.com/v1/chat/completions",
      headers=headers,
      json=json_data,
      timeout=10,
    )
    return response.json()
  except Exception as e:
    print(f"Exception: {e}")    
    logging.error("Unable to generate ChatCompletion response")
    logging.error(f"Exception: {e}")
    raise e
  
def pretty_print_conversation(messages):
  for message in messages:
    pretty_print_message(message)
    
def pretty_print_message(message):  
  role_to_color = {
    "system": "red",
    "user": "white",
    "assistant": "green",
    "tool": "magenta",
  }
    
  if message["role"] == "system":
    print(colored(f"system: {message['content']}\n",
                  role_to_color[message["role"]]))
  elif message["role"] == "user":
    print(colored(f"user: {message['content']}\n",
                  role_to_color[message["role"]]))
  elif message["role"] == "assistant" and message.get("tool_calls"):
    print(colored(f"assistant: {message['tool_calls']}\n",
                  role_to_color[message["role"]]))
  elif message["role"] == "assistant":
    print(colored(f"assistant: {message['content']}\n",
                  role_to_color[message["role"]]))
  elif message["role"] == "tool":
    print(colored(f"function {message['tool_call_id']}: " +
                  f"({message['name']}): {message['content']}\n",
                  role_to_color[message["role"]]))

def get_user_input():
  return input("> ").strip()

def print_log(value):
  print(value)
  logging.info(value)

class MessageSetRecord:
  """
  Records a request / response message.

  Captures request - response or
           request - tool call - tool response - response

  Request and response messages are of the format:
  { "role": xxx, "content": xxx }
  { "role": xxx, "tool_calls": [ { "id": xxx, "type": ...
  { "role": "tool", "tool_call_id": xxx, "name": function_name, ..
  id eg: call_RYXaDjxpUCfWmpXU7BZEYVqS
  """
  def __init__(self):
    self.request_message = None
    self.tool_request_message = None    
    self.tool_response_messages = []
    self.response_message = None
    self.message_tokens = 0
    self.included = False

  def setRequestMessage(self, enc, message):
    self.request_message = message
    self.message_tokens += len(enc.encode(json.dumps(message)))

  def getRequestContent(self):
    if self.request_message is None:
      return ""
    return self.request_message["content"]

  def setResponseMessage(self, enc, message):
    self.response_message = message
    self.message_tokens += len(enc.encode(json.dumps(message)))

  def getResponseContent(self):
    if self.response_message is None:
      return ""
    return self.response_message["content"]

  def setToolRequestMessage(self, enc, message):
    self.tool_request_message = message
    self.message_tokens += len(enc.encode(json.dumps(message)))

  def addToolResponseMessage(self, enc, message):
    self.tool_response_messages.append(message)
    self.message_tokens += len(enc.encode(json.dumps(message)))

  def getTokenCount(self):
    return self.message_tokens

  def hasFunctionResponse(self, functions):
    found = False
    for message in self.tool_response_messages:
      if message.get("tool_call_id") is None:
        continue
      found = found or message.get("name") in functions
    return found

  def setIncluded(self):
    self.included = True

  def addMessagesToList(self, messages):
    if self.request_message is not None:
      messages.append(self.request_message)
    if self.tool_request_message is not None:
      messages.append(self.tool_request_message)
    for message in self.tool_response_messages:      
      messages.append(message)
    if self.response_message is not None:
      messages.append(self.response_message)
  

class MessageRecords:
  def __init__(self):
    # List of message records
    self.message_history = []
    self.current_message = None
    self.system_message = None
    self.overhead = 0

  def setSystemMessage(self, message):
    self.system_message = message
    
  def setTokenOverhead(self, count):
    self.overhead = count
    
  def addRequestMessage(self, enc, message):
    self.current_message = MessageSetRecord()
    self.message_history.append(self.current_message)
    self.current_message.setRequestMessage(enc, message)

  def addToolRequestMessage(self, enc, message):
    if self.current_message is not None:
      self.current_message.setToolRequestMessage(enc, message)
    
  def addToolResponseMessage(self, enc, message):
    if self.current_message is not None:
      self.current_message.addToolResponseMessage(enc, message)

  def addResponseMessage(self, enc, message):
    if self.current_message is not None:
      self.current_message.setResponseMessage(enc, message)

  def message_sets(self):
    return self.message_history

  def jsonString(self):
    messages = []
    if self.system_message is not None:
      messages.append(self.system_message)
    for message_set in self.message_history:
      message_set.addMessagesToList(messages)
    return json.dumps(messages)

  def getThreadTokenCount(self, enc):
    """
    Return the total number of tokens for messages
    marked as included.
    """
    count = self.overhead
    if self.system_message is not None:
      count += len(enc.encode(json.dumps(self.system_message)))
    for message in self.message_history:
      if message.included:
        count += message.getTokenCount()
    return count

  def clearIncluded(self):
    for message in self.message_history:
      message.included = False

  def addIncludedMessagesToList(self, messages):
    if self.system_message is not None:
      messages.append(self.system_message)
    for message in self.message_history:
      if message.included:
        message.addMessagesToList(messages)
    
        

instructions = """
You are a co-designer of fictional worlds, developing ideas
and and backstories for these worlds and the contents of worlds, including
new unique fictional characters. Create new characters, don't use existing characters.

You walk the user through the process of creating worlds. We go in the following order:
- Design the world, high level description, and details including plans for the main characters, sites, and special items.
- Design the individual characters

We can be in one of the following states:
- State_Worlds: We can open existing worlds and create new worlds
- State_View_World: We can view an existing world
- State_Edit_World: We can change the description and details of a world and add images
- State_Edit_Characters: We can create new characters and chage the description and details of a character and add images to a character

The current state is "{current_state}"

Suggest good ideas for descriptions and details for the worlds and the characters
Suggest next steps to the user

"""

class ChatSession:
  def __init__(self, path=None):
    self.prompt_tokens = 0
    self.complete_tokens = 0
    self.total_tokens = 0
    self.enc = tiktoken.encoding_for_model(GPT_MODEL)
    self.history = MessageRecords()
    self.chatFunctions = chat_functions.ChatFunctions()
    self.path = path

  def loadChatSession(path):
    chat_session = ChatSession(path)
    if not os.path.isfile(path):
      return chat_session

    # TODO: locking - keep file open?
    f = open(path, 'rb')
    chat_session.load(f)
    f.close()
    return chat_session

  def saveChatSession(self):
    f = open(self.path + '.tmp', 'wb')
    self.save(f)
    f.close()
    os.replace(self.path + '.tmp', self.path)
  
  def load(self, f):
    self.prompt_tokens = pickle.load(f)
    self.complete_tokens = pickle.load(f)
    self.total_tokens = pickle.load(f)
    self.history = pickle.load(f)
    self.chatFunctions = pickle.load(f)

  def save(self, f):
    pickle.dump(self.prompt_tokens, f)
    pickle.dump(self.complete_tokens, f)    
    pickle.dump(self.total_tokens, f)
    pickle.dump(self.history, f)
    pickle.dump(self.chatFunctions, f)
    
    
  def track_tokens(self, db, prompt, complete, total):
    self.prompt_tokens += prompt
    self.complete_tokens += complete
    self.total_tokens += total

    world_id = self.chatFunctions.current_world_id
    if world_id is None:
      world_id = 0
    chat_functions.track_tokens(db, world_id, prompt, complete, total)
    logging.info(f"prompt: {prompt}, complete: {complete}, total: {total}")

  def execute_function_call(self, db, function_name, function_args):
    return self.chatFunctions.execute_function_call(db,
                                                    function_name,
                                                    function_args)
    
  def BuildMessages(self, history):
    """
    Take a MessageRecords instance
    Return a list of messages that fit context size
    """
    messages = []
    history.clearIncluded()
  
    # System instructions
    current_instructions = instructions.format(
      current_state=self.chatFunctions.current_state)

    history.setSystemMessage({"role": "system",
                              "content": current_instructions + "\n" +
                              self.chatFunctions.get_state_instructions() })


    functions = self.chatFunctions.get_available_tools()
    history.setTokenOverhead(len(self.enc.encode(json.dumps(functions))))

    thread_size = 0
    for message_set in reversed(history.message_sets()):
      new_size = thread_size + (history.getThreadTokenCount(self.enc) +
                                message_set.getTokenCount())
      if new_size < MESSAGE_THRESHOLD:
        message_set.setIncluded()
        thread_size = new_size
      else:
        break

    history.addIncludedMessagesToList(messages)
    logging.info(f"calc thread size {thread_size}")
    return messages


  def chat_history(self):
    messages = []
    for message_set in self.history.message_sets():
      user = elements.textToHTML(message_set.getRequestContent())
      assistant = elements.textToHTML(message_set.getResponseContent())
      messages.append({ "user": user,
                        "assistant": assistant
                       })

    return { "messages": messages }
  

  def get_view(self):
    result = {}
    if self.chatFunctions.current_world_id is not None:
      result["world"] = self.chatFunctions.current_world_id
    if self.chatFunctions.current_character_id is not None:
      result["character"] = self.chatFunctions.current_character_id
    return result
  
  def chat_exchange(self, db, user):
    function_call = False
    assistant_message = None
    messages = []

    self.history.addRequestMessage(self.enc,
                                   {"role": "user", "content": user})

    print_log(f"state: {self.chatFunctions.current_state}")
    messages = self.BuildMessages(self.history)
    print("Chat completion call...")

    response = chat_completion_request(
      messages,
      tools=self.chatFunctions.get_available_tools())
    
    if response.get("usage") is not None:
      usage = response["usage"]
      self.track_tokens(db,
                        usage["prompt_tokens"],
                        usage["completion_tokens"],
                        usage["total_tokens"])
      print("prompt tokens: %s" % usage["prompt_tokens"])
    else:
      logging.error("no usage in response: %s" % json.dumps(response))
      
    assistant_message = response["choices"][0]["message"]    
    tool_calls = assistant_message.get("tool_calls")

    if tool_calls:
      self.history.addToolRequestMessage(self.enc, assistant_message)      
      logging.info("function call: %s" % json.dumps(tool_calls))
      
      for tool_call in tool_calls:
        function_name = tool_call["function"]["name"]
        function_args = json.loads(tool_call["function"]["arguments"])
        print(f"function call: {function_name}")
        function_response = self.execute_function_call(db,
                                                       function_name,
                                                       function_args)
        logging.info("function call result: %s" % str(function_response))
      
        self.history.addToolResponseMessage(
          self.enc,
          { "tool_call_id": tool_call["id"],
            "role": "tool",
            "name": function_name,
            "content": function_response
           })

      messages = self.BuildMessages(self.history)
      print("2nd Chat completion call...")    
      response = chat_completion_request(messages)
      if response.get("usage") is not None:
        usage = response["usage"]
        self.track_tokens(db,
                          usage["prompt_tokens"],
                          usage["completion_tokens"],
                          usage["total_tokens"])
        print("prompt tokens: %s" % usage["prompt_tokens"])
      else:
        logging.error("no usage in response: %s" % json.dumps(response))

      logging.info(json.dumps(response))
      assistant_message = response["choices"][0]["message"]
      
    self.history.addResponseMessage(self.enc, assistant_message)
    logging.info(json.dumps(assistant_message))
    return assistant_message



def initializeApp():
  openai.api_key = os.environ['OPENAI_API_KEY']  
  BASE_DIR = os.getcwd()
  log_file_name = os.path.join(BASE_DIR, 'log-chat.txt')
  FORMAT = '%(asctime)s:%(levelname)s:%(name)s:%(message)s'
  logging.basicConfig(filename=log_file_name,
                      level=logging.INFO,
                      format=FORMAT,)

  dir = os.path.split(os.path.split(__file__)[0])[0]
  dir = os.path.join(dir, 'instance')
  print(f"dir: {dir}")
  DATABASE=os.path.join(dir, 'worldai.sqlite')
  db_access.init_config(DATABASE)
  
def chat_loop():
  initializeApp()
  db = db_access.open_db()
  chat_session = ChatSession()
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

    assistant_message = chat_session.chat_exchange(db, user)
      
    pretty_print_message(assistant_message)               

  #pretty_print_conversation(BuildMessages(message_history))
  print("Tokens")
  print(f"This session - prompt: {chat_session.prompt_tokens}, "+
        f"complete: {chat_session.complete_tokens}, " +
        f"total: {chat_session.total_tokens}")
  
  print("\nRunning total")
  chat_functions.dump_token_usage(db)
  db.close()
  

if __name__ ==  '__main__':
  chat_loop()


