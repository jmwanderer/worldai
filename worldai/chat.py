#!/usr/bin/env python3
"""
Text chat client that can make function calls update world model

From: https://cookbook.openai.com/examples/how_to_call_functions_with_chat_models
"""

import os
import json
import openai
import requests
from tenacity import retry, wait_random_exponential, stop_after_attempt
from termcolor import colored
import tiktoken

from . import elements
from . import chat_functions

GPT_MODEL = "gpt-3.5-turbo-0613"
openai.api_key = os.environ['OPENAI_API_KEY']

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
  print(f"prompt: {prompt}, complete: {complete}, total: {total}")
  

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
      print("no usage in response: %s" % json.dumps(response.json()))
    return response
  except Exception as e:
    print("Unable to generate ChatCompletion response")
    print(f"Exception: {e}")
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
You are a co-designer of fictional worlds, helping the user come up
with ideas and backstories for these worlds and the contents of worlds.
You walk the user through the process of creating worlds, starting
with the high level vision and developing further details.

All worlds include main characters, key sites, and special items.
We come up with new unique fictional characters.

Worlds, characters, sites, and items have:
- a unique id
- a name
- a high level description
- detailed information

Content for words, characters, sites, and items are saved by calling update functions.

Keep the description short, longer information goes in the details field.

Suggest next steps to the user, but seek approval before creating new content.

"Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous."
"""

enc = tiktoken.encoding_for_model(GPT_MODEL)

messages_history = []
def build_messages():
  messages = []
  # System instructions
  messages.append({"role": "system",
                   "content": instructions })
  # State instructions
  messages.append({"role": "user",
                   "content":
                   chat_functions.get_state_instructions()})
  # Message history
  messages.extend(messages_history)

  thread_size = 0
  for message in messages:
    if message["content"] is not None:
      thread_size += len(enc.encode(message["content"]))
  print(f"message thread size: {thread_size}")

  return messages

function_call = False
assistant_message = None

messages = []

while True:
  if not function_call:
    user = input("> ").strip()
    if user == 'exit':
      break
    if len(user) == 0:
      continue
    messages_history.append({"role": "user", "content": user})
    print("user len: %d" % len(enc.encode(user)))
  else:
    print("Calling function %s: " % assistant_message["function_call"])
    content = chat_functions.execute_function_call(
      assistant_message["function_call"])
    messages_history.append({"role": "function",
                             "name": assistant_message["function_call"]["name"],
                             "content": content})

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
  else:
    function_call = False
    pretty_print_message(assistant_message)
    print("msg result: %d" % len(enc.encode(assistant_message["content"])))    


pretty_print_conversation(messages)
  
print("Tokens")
print(f"This session - prompt: {prompt_tokens}, complete: {complete_tokens}, total: {total_tokens}")
print("\nRunning total")
chat_functions.dump_token_usage()

