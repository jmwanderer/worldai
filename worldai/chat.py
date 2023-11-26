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
    usage = response.json()["usage"]
    track_tokens(usage["prompt_tokens"], usage["completion_tokens"],
                 usage["total_tokens"])
    return response
  except Exception as e:
    print("Unable to generate ChatCompletion response")
    print(f"Exception: {e}")
    return e

  
def pretty_print_conversation(messages):
  role_to_color = {
    "system": "red",
    "user": "white",
    "assistant": "green",
    "function": "magenta",
  }
    
  for message in messages:
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

def print_assistant(message):
  print(colored(f"{message['content']}\n", "green"))


dir = os.path.split(os.path.split(__file__)[0])[0]
dir = os.path.join(dir, 'instance')
print(f"dir: {dir}")
chat_functions.init_config(dir, "worldai.sqlite")

for func in chat_functions.functions:
  func_str = json.dumps(func)
  print(func_str)


instructions = """
You are a helpful designer of fictional worlds.
Worlds haved characters, sites, and items.
All of these have a unique id, a name, a high level description, and details.
We come up with new unique fictional characters.

When we develop content for a world, the content is saved by calling
update functions.

You walk the user through the process of creating worlds, starting with the high level vision and developing further details.

"Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous."
"""
messages = []
enc = tiktoken.encoding_for_model(GPT_MODEL)
messages.append({"role": "system",
                 "content": instructions })
print("sys len: %d" % len(enc.encode(messages[0]["content"])))
function_call = False
assistant_message = None


while True:
  if not function_call:
    user = input("> ").strip()
    if user == 'exit':
      break
    messages.append({"role": "user", "content": user})
    print("user len: %d" % len(enc.encode(user)))
  else:
    content = chat_functions.execute_function_call(
      assistant_message["function_call"])
    print("function content: %s" % json.dumps(content))
    messages.append({"role": "function",
                     "name": assistant_message["function_call"]["name"],
                     "content": content})
    print("len func result: %d" % len(enc.encode(content)))

  chat_response = chat_completion_request(
    messages, functions=chat_functions.functions
  )
  print(json.dumps(chat_response.json()))
  assistant_message = chat_response.json()["choices"][0]["message"]
  messages.append(assistant_message)
  
  # Check function call
  if assistant_message.get("function_call"):
    function_call = True
    print("making a function call: %s" %
          (assistant_message.get("function_call")))
  else:
    function_call = False
    print("msg result: %d" % len(enc.encode(assistant_message["content"])))    
    print_assistant(assistant_message)


pretty_print_conversation(messages)
  
print("Total tokens")
print(f"prompt: {prompt_tokens}, complete: {complete_tokens}, total: {total_tokens}")

chat_functions.dump_token_usage()

