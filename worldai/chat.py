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
from tenacity import retry, wait_random_exponential, stop_after_attempt
from termcolor import colored
import tiktoken

from . import elements
from . import chat_functions

GPT_MODEL = "gpt-3.5-turbo-0613"
openai.api_key = os.environ['OPENAI_API_KEY']


BASE_DIR = os.getcwd()
log_file_name = os.path.join(BASE_DIR, 'log-chat.txt')
FORMAT = '%(asctime)s:%(levelname)s:%(name)s:%(message)s'
logging.basicConfig(filename=log_file_name,
                    level=logging.INFO,
                    format=FORMAT,)


prompt_tokens = 0
complete_tokens = 0
total_tokens = 0

def track_tokens(prompt, complete, total):
  global prompt_tokens
  global complete_tokens
  global total_tokens
  prompt_tokens += prompt
  complete_tokens += complete
  total_tokens += total
  chat_functions.track_tokens(0, prompt, complete, total)
  logging.info(f"prompt: {prompt}, complete: {complete}, total: {total}")
  

@retry(wait=wait_random_exponential(multiplier=1, max=40),
       stop=stop_after_attempt(3))
def chat_completion_request(messages, functions=None, function_call=None,
                            model=GPT_MODEL):
  headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + openai.api_key,
  }
  json_data = {"model": model, "messages": messages}
  if functions is not None:
    json_data.update({"functions": functions})
  if function_call is not None:
    json_data.update({"function_call": function_call})
  try:
    response = requests.post(
      "https://api.openai.com/v1/chat/completions",
      headers=headers,
      json=json_data,
      timeout=10,
    )
    if response.json().get("usage") is not None:
      usage = response.json()["usage"]
      track_tokens(usage["prompt_tokens"], usage["completion_tokens"],
                   usage["total_tokens"])
    else:
      logging.error("no usage in response: %s" % json.dumps(response.json()))
    return response
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
    "function": "magenta",
  }
    
  if message["role"] == "system":
    print(colored(f"system: {message['content']}\n",
                  role_to_color[message["role"]]))
  elif message["role"] == "user":
    print(colored(f"user: {message['content']}\n",
                  role_to_color[message["role"]]))
  elif message["role"] == "assistant" and message.get("function_call"):
    print(colored(f"assistant: {message['function_call']}\n",
                  role_to_color[message["role"]]))
  elif message["role"] == "assistant" and not message.get("function_call"):
    print(colored(f"assistant: {message['content']}\n",
                  role_to_color[message["role"]]))
  elif message["role"] == "function":
    print(colored(f"function ({message['name']}): {message['content']}\n",
                  role_to_color[message["role"]]))

dir = os.path.split(os.path.split(__file__)[0])[0]
dir = os.path.join(dir, 'instance')
print(f"dir: {dir}")
chat_functions.init_config(dir, "worldai.sqlite")


instructions = """
You are a co-designer of fictional worlds, developing ideas
and and backstories for these worlds and the contents of worlds, including
new unique fictional characters.

You walk the user through the process of creating worlds. We go in the following order:
- Design the world, high level description, and details including plans for the main characters, sites, and special items.
- Design the individual characters

We can be in one of the following states:
- State_Worlds: We can open existing worlds and create new worlds
- State_View_World: We can view an existing world
- State_Edit_World: We can change the description and details of a world
- State_Characters: We can open existing characters and create new characters
- State_Edit_Character: We can chage the description and details of a character

The current state is "{current_state}"

Keep the description short, longer information goes in the details field.

Suggest next steps to the user
Suggest description and details for worlds and characters

"Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous."
"""

enc = tiktoken.encoding_for_model(GPT_MODEL)
MESSAGE_THRESHOLD=2_000

messages_history = []
def build_messages():
  messages = []
  # System instructions

  current_instructions = instructions.format(
    current_state=chat_functions.current_state)
  sys_message = {"role": "system",
                 "content": current_instructions + "\n" +
                 chat_functions.get_state_instructions() }

  length = len(enc.encode(json.dumps(sys_message)))
  functions = chat_functions.get_available_functions()
  length += len(enc.encode(json.dumps(functions)))
  logging.info(f"sys + func: {length} tokens")
  logging.info(sys_message)
  messages.append(sys_message)

  for message in reversed(messages_history):
    msg_len = len(enc.encode(json.dumps(message)))
    if length + msg_len < MESSAGE_THRESHOLD:
      messages.insert(1, message)
    else:
      # Since we didn't include all messages, add extra context
      context = chat_functions.get_context() 
      context_message = { "role": "assistant",
                          "content": context }
      if (context) is not None:
        msg_len = len(enc.encode(json.dumps(context_message)))
        length += msg_len
        messages.insert(1, context_message)
      break

  logging.info(f"message thread size: {length}")
  return messages



function_call = False
assistant_message = None
messages = []

func_call = { 'name': 'ListWorlds',
              'arguments': '{}' }
content = chat_functions.execute_function_call(func_call)
values = json.loads(content)

print("Welcome to the world builder!\n")
print("You can create and design worlds with main characters, key sites, and special items.")
if len(values) == 0:
  print("You have no worlds yet created.")
else:
  print("You have %d worlds created:" % len(values))
  for value in values:
    print("- %s" % value["name"])

print("")
print("What do you want to do?\n")

while True:
  if not function_call:
    try:
      user = input("> ").strip()
    except EOFError:
      break
    if user == 'exit':
      break
    if len(user) == 0:
      continue
    messages_history.append({"role": "user", "content": user})
    logging.info("user len: %d" % len(enc.encode(user)))
  else:
    print("function call: %s" % assistant_message["function_call"])
    content = chat_functions.execute_function_call(
      assistant_message["function_call"])
    logging.info(content)
    messages_history.append({"role": "function",
                             "name": assistant_message["function_call"]["name"],
                             "content": content})
  print("state: %s" % chat_functions.current_state)
  messages = build_messages()
  print("Chat completion call...")
  try:
    chat_response = chat_completion_request(
      messages,
      functions=chat_functions.get_available_functions()
    )
  except Exception as e:
    break
  
  assistant_message = chat_response.json()["choices"][0]["message"]
  messages_history.append(assistant_message)
  
  # Check function call
  if assistant_message.get("function_call"):
    function_call = True
    logging.info("msg result: %d" %
          len(enc.encode(json.dumps(assistant_message["function_call"]))))
  else:
    function_call = False
    pretty_print_message(assistant_message)  
    logging.info("msg result: %d" % len(enc.encode(assistant_message["content"])))    


pretty_print_conversation(build_messages())
  
print("Tokens")
print(f"This session - prompt: {prompt_tokens}, complete: {complete_tokens}, total: {total_tokens}")
print("\nRunning total")
chat_functions.dump_token_usage()

