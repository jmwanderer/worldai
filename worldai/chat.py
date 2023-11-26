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

from . import elements
from . import chat_functions

GPT_MODEL = "gpt-3.5-turbo-0613"
openai.api_key = os.environ['OPENAI_API_KEY']

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
  

messages = []
messages.append({"role": "system",
                 "content": "Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous."})

function_call = False
assistant_message = None

while True:
  if not function_call:
    user = input("> ").strip()
    if user == 'exit':
      break
    messages.append({"role": "user", "content": user})
  else:
    content = chat_functions.execute_function_call(
      assistant_message["function_call"])
    messages.append({"role": "function",
                     "name": assistant_message["function_call"]["name"],
                     "content": content})

  chat_response = chat_completion_request(
    messages, functions=chat_functions.functions
  )
  assistant_message = chat_response.json()["choices"][0]["message"]
  messages.append(assistant_message)
  
  # Check function call
  if assistant_message.get("function_call"):
    function_call = True
    print("making a function call: %s" %
          (assistant_message.get("function_call")))
  else:
    function_call = False    
    print_assistant(assistant_message)


pretty_print_conversation(messages)
  



