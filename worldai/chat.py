#!/usr/bin/env python3
"""
Text chat client that can make function calls update world model

From: https://cookbook.openai.com/examples/how_to_call_functions_with_chat_models
"""

import os
import time
import json
import logging
import openai
import requests
import pickle
import io

from tenacity import retry, wait_random_exponential, stop_after_attempt
from termcolor import colored
import tiktoken

from . import db_access
from . import elements
from . import chat_functions

GPT_MODEL = "gpt-3.5-turbo-1106"
# Can be higher, but save $$$ with some potential loss in perf
MESSAGE_THRESHOLD=3_000
TESTING = False

TEST_RESPONSE="""
{"id": "chatcmpl-8VpkBh4MOnvETZRZUphRo0QXk9tdN", "object": "chat.completion", "created": 1702597763, "model": "gpt-3.5-turbo-1106", "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hello! How can I assist you today? If you have any questions or need assistance with world-building, character creation, or storytelling, feel free to ask!"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 2074, "completion_tokens": 33, "total_tokens": 2107}, "system_fingerprint": "fp_f3efa6edfc"}
"""

@retry(wait=wait_random_exponential(multiplier=1, max=40),
       stop=stop_after_attempt(3))
def chat_completion_request(messages, tools=None,
                            tool_choice=None, model=GPT_MODEL):
  headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + openai.api_key,
  }
  json_data = {"model": model, "messages": messages}
  if tools is not None:
    json_data.update({"tools": tools})
  if tool_choice is not None:
    json_data.update({"tool_choice": tool_choice})

  try:
    if TESTING:
      return json.loads(TEST_RESPONSE)
    
    response = requests.post(
      "https://api.openai.com/v1/chat/completions",
      headers=headers,
      json=json_data,
      timeout=20,
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


def log_chat_message(messages, assistant_message):
  """
  If enabled, write a timestamped file with messages
  """
  dir = os.path.join(chat_functions.IMAGE_DIRECTORY, "messages")
  if not os.path.exists(dir):
    os.makedirs(dir)

  out = { "message": messages,
          "assistant": assistant_message }
  ts = time.time()
  filename = f"message.{ts}.txt"
  path = os.path.join(dir, filename)
  f = open(path, "w")
  f.write(json.dumps(out, indent=4))
  f.close()

  
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
    # Array of ToolRequestMesage
    self.tool_messages = []
    self.response_message = None
    self.message_tokens = 0
    self.included = False

  class ToolRequestMessage:
    def __init__(self):
      self.request_message = None
      self.response_messages = []

  def _recursiveValueCount(enc, elements):
    count = 0
    for key, value in elements.items():
      if value is None:
        continue

      if isinstance(value, dict):
        count += MessageSetRecord._recursiveValueCount(enc, value)
      elif isinstance(value, list):
        for entry in value:
          if isinstance(entry, dict):
            count += MessageSetRecord._recursiveValueCount(enc, entry)
          else:
            count += len(enc.encode(entry))
      else:
        count += len(enc.encode(value))
        if key == "name":
          count -= 1
    return count
  
  def _updateTokenCount(self, enc, message):
    """
    Called for each add message.
    """
    self.message_tokens += 4
    self.message_tokens += MessageSetRecord._recursiveValueCount(enc, message)
        
  def setRequestMessage(self, enc, message):
    self.request_message = message
    self._updateTokenCount(enc, message)

  def getRequestContent(self):
    if self.request_message is None:
      return ""
    return self.request_message["content"]

  def setResponseMessage(self, enc, message):
    self.response_message = message
    self._updateTokenCount(enc, message)    

  def getResponseContent(self):
    if self.response_message is None:
      return ""
    return self.response_message["content"]

  def addToolRequestMessage(self, enc, message):
    record = MessageSetRecord.ToolRequestMessage()
    record.request_message = message
    self.tool_messages.append(record)
    self._updateTokenCount(enc, message)    

  def addToolResponseMessage(self, enc, message):
    record = self.tool_messages[-1]
    record.response_messages.append(message)
    self._updateTokenCount(enc, message)        

  def getTokenCount(self):
    return self.message_tokens

  def hasToolCall(self, name, args):
    """
    Check if the function name and arguments are in a tool
    call message. The args can be a subset.
    """
    for message in self.tool_messages:
      for tool_call in message.request_message.get("tool_calls"):
        function_name = tool_call["function"]["name"]
        if function_name == name:
          arg_str = tool_call["function"]["arguments"]
          function_args = json.loads(arg_str)
          args_check = True
          for key, value in args.items():
            if function_args.get(key) != value:
              args_check = False
          if args_check:
            return True
    return False

  def setIncluded(self):
    self.included = True

  def addMessagesToList(self, messages):
    if self.request_message is not None:
      messages.append(self.request_message)

    for record in self.tool_messages:
      messages.append(record.request_message) 
      for message in record.response_messages:
        messages.append(message)
    if self.response_message is not None:
      messages.append(self.response_message)
  

class MessageRecords:
  def __init__(self):
    # List of message records
    self.message_history = []
    self.current_message = None
    self.system_message = None
    self.function_tokens = 0

  def setSystemMessage(self, message):
    self.system_message = message

  def _countFunctionTokens(self, enc, function):
    count = len(enc.encode(function["name"]))
    count += len(enc.encode(function["description"]))
    if "parameters" in function:
      parameters = function["parameters"]
      if "properties" in parameters:
        for key in parameters["properties"]:
          count += len(enc.encode(key))
          values = parameters["properties"][key]
          for field in values:
            if field == 'type':
              count += 2
              count += len(enc.encode(values['type']))

            elif field == 'description':
              count += 2
              count += len(enc.encode(values['description']))

            elif field == 'enum':
              count -= 3
              for entry in values['enum']:
                count += 3
                count += len(enc.encode(entry))
        count += 11

    return count
      
  def setFunctions(self, enc, functions):
    self.function_tokens = 0    
    if functions is None:
      return

    self.function_tokens = 12
    for entry in functions:
      self.function_tokens += self._countFunctionTokens(enc, entry["function"])

  def isEmpty(self):
    return len(self.message_history) == 0
    
  def addRequestMessage(self, enc, message):
    self.current_message = MessageSetRecord()
    self.message_history.append(self.current_message)
    self.current_message.setRequestMessage(enc, message)

  def addToolRequestMessage(self, enc, message):
    if self.current_message is not None:
      self.current_message.addToolRequestMessage(enc, message)
    
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
    count = self.function_tokens
    if self.system_message is not None:
      count += 4
      for key, value in self.system_message.items():
        count += len(enc.encode(value))
        if key == "name":
          count -= 1

    for message in self.message_history:
      if message.included:
        count += message.getTokenCount()
    return count + 2

  def clearIncluded(self):
    for message in self.message_history:
      message.included = False

  def addIncludedMessagesToList(self, messages):
    if self.system_message is not None:
      messages.append(self.system_message)
    for message in self.message_history:
      if message.included:
        message.addMessagesToList(messages)


  def hasToolCall(self, name, args):
    """
    Check for matching function call in included messages
    """
    for message in self.message_history:
      if message.included and message.hasToolCall(name, args):
        return True
    return False
    

def get_thread(db, session_id):
  c = db.execute("SELECT thread FROM threads WHERE id = ? ",
                 (session_id,))
  r = c.fetchone()
  if r is not None:
    thread = r[0]
    return thread
  return None

def save_thread(db, session_id, thread):
  now = time.time()
  c = db.execute("SELECT count(*) FROM threads WHERE id = ? ",
                 (session_id,))
  if c.fetchone()[0] == 0:
    # INSERT
    
    q = db.execute("INSERT INTO threads VALUES (?, ?, ?, ?)",
                   (session_id, now, now, thread))
  else:
    # UPDATE
    q = db.execute("UPDATE threads SET thread = ?, updated = ? WHERE id = ?",
                   (thread, now, session_id))
  db.commit()

def delete_thread(db, session_id)  :
  q = db.execute("DELETE FROM threads WHERE id = ?",
                   (session_id,))
  db.commit()

  
class ChatSession:
  def __init__(self, id=None):
    self.prompt_tokens = 0
    self.complete_tokens = 0
    self.total_tokens = 0
    self.enc = tiktoken.encoding_for_model(GPT_MODEL)
    self.history = MessageRecords()
    self.chatFunctions = chat_functions.ChatFunctions()
    self.id = id
    self.madeChanges = False

  def loadChatSession(db, session_id):
    chat_session = ChatSession(session_id)
    thread = get_thread(db, session_id)
    if thread is not None:
      f = io.BytesIO(thread)
      chat_session.load(f)
      f.close()
    return chat_session

  def saveChatSession(self, db):
    f = io.BytesIO()
    self.save(f)
    thread = f.getvalue()
    save_thread(db, self.id, thread)
    f.close()

  def deleteChatSession(self, db):
    delete_thread(db, self.id)
    
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
    

  def madeModifications(self):
    return self.madeChanges
  
  def track_tokens(self, db, prompt, complete, total):
    self.prompt_tokens += prompt
    self.complete_tokens += complete
    self.total_tokens += total

    world_id = self.chatFunctions.getCurrentWorldID()
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
    current_instructions = chat_functions.GLOBAL_INSTRUCTIONS.format(
      current_state=self.chatFunctions.current_state)

    history.setSystemMessage({"role": "system",
                              "content": current_instructions + "\n" +
                              self.chatFunctions.get_state_instructions() })

    functions = self.chatFunctions.get_available_tools()
    history.setFunctions(self.enc, functions)

    thread_size = 0
    for message_set in reversed(history.message_sets()):
      new_size = (history.getThreadTokenCount(self.enc) +
                  message_set.getTokenCount())
      if new_size < MESSAGE_THRESHOLD:
        message_set.setIncluded()
        thread_size = new_size
      else:
        break

    history.addIncludedMessagesToList(messages)
    logging.info(f"calc thread size {thread_size}")
    return messages


    
  def checkToolChoice(self):
    """
    Determine if we need to fetch additional information
    to act on requests.

    Use the current state and the presense of included messages
    to make decisions.
    """
    tool_func = None
    if self.chatFunctions.current_state == chat_functions.STATE_WORLDS:
      if not self.history.hasToolCall("ListWorlds", {}):
        tool_func = "ListWorlds"
    elif (self.chatFunctions.current_state ==
          chat_functions.STATE_CHARACTERS):
      if not self.history.hasToolCall("ListCharacters", {}):
        tool_func = "ListCharacters"
    elif (self.chatFunctions.current_state ==
          chat_functions.STATE_ITEMS):
      if not self.history.hasToolCall("ListItems", {}):
        tool_func = "ListItems"
    elif (self.chatFunctions.current_state ==
          chat_functions.STATE_SITES):
      if not self.history.hasToolCall("ListSites", {}):
        tool_func = "ListSites"

    if tool_func is not None:
      return { "type": "function",
               "function": { "name": tool_func }}
    return None
    

  def chat_history(self):
    messages = []
    for message_set in self.history.message_sets():
      user = elements.textToHTML(message_set.getRequestContent())
      assistant = chat_functions.parseResponseText(
        message_set.getResponseContent())
      
      messages.append({ "user": user,
                        "assistant": assistant
                       })

    return { "messages": messages }
  

  def get_view(self):
    return self.chatFunctions.current_view.json()

  def set_view(self, view):
    self.chatFunctions.next_view = view
  
  def chat_exchange(self, db, user):
    function_call = False
    assistant_message = None
    messages = []
    tool_choice = None

    self.chatFunctions.clearChanges()
    self.history.addRequestMessage(self.enc,
                                   {"role": "user", "content": user})
    call_count = 0
    done = False
    while not done:
      logging.info(f"state: {self.chatFunctions.current_state}")
      logging.info("current view: %s",
                   self.chatFunctions.current_view.jsonStr())
      
      messages = self.BuildMessages(self.history)
      tool_choice = self.checkToolChoice()

      call_count += 1
      print_log(f"[{call_count}]: Chat completion call...")
      # Limit tools call to 5
      if call_count < 6:
        tools=self.chatFunctions.get_available_tools()
      else:
        tools = None
        tool_choice=None

      # Make completion request call with the messages we have
      # selected from the message history and potentially
      # available tools and specified tool choice.
      #logging.info(json.dumps(messages))
      response = chat_completion_request(
        messages,
        tools=tools,
        tool_choice=tool_choice
      )
      logging.info("Response: %s", json.dumps(response))

      # Clear tool choice, only force a tool call on the first request.
      tool_choice = None

      # Check for an error
      if response.get("usage") is not None:
        usage = response["usage"]
        self.track_tokens(db,
                          usage["prompt_tokens"],
                          usage["completion_tokens"],
                          usage["total_tokens"])
        print_log("prompt tokens: %s" % usage["prompt_tokens"])
      else:
        logging.error("no usage in response")

      # Process resulting message
      # TODO: handle error messages.
      if response.get("choices") is not None:
        assistant_message = response["choices"][0]["message"]
        log_chat_message(messages, assistant_message)        

      elif response.get("error"):
        log_chat_message(messages, response["error"])
      
      tool_calls = assistant_message.get("tool_calls")

      if tool_calls: 
        # Make requested calls to tools.
        self.history.addToolRequestMessage(self.enc, assistant_message)      
      
        for tool_call in tool_calls:
          function_name = tool_call["function"]["name"]
          function_args = json.loads(tool_call["function"]["arguments"])
          print_log(f"function call: {function_name}")
          function_response = self.execute_function_call(db,
                                                         function_name,
                                                         function_args)
          logging.info("function call result: %s" % str(function_response))
      
          self.history.addToolResponseMessage(
            self.enc,
            { "tool_call_id": tool_call["id"],
              "role": "tool",
              "name": function_name,
              "content": json.dumps(function_response)
             })
      else:
        # Otherwise, just a response from the assistant, we are done.
        self.history.addResponseMessage(self.enc, assistant_message)
        done = True
        
    # Return result
    self.madeChanges = self.chatFunctions.madeChanges() 
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
  chat_functions.IMAGE_DIRECTORY = dir
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


