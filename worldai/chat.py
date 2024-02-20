#!/usr/bin/env python3
"""
Text chat client that can make function calls update world model

From: https://cookbook.openai.com/examples/how_to_call_functions_with_chat_models
"""

import json
import logging
import os
import time
import typing

import openai
import pydantic
import requests
import tiktoken
from tenacity import retry, stop_after_attempt, wait_random_exponential
from termcolor import colored

from . import chat_functions, message_records, info_set

# TODO:
# Update chat messages:
#  1. Add a message id
#  2. change assistant to reply
#

GPT_MODEL = "gpt-3.5-turbo-0125"
# GPT_MODEL = "gpt-3.5-turbo-1106"
# GPT_MODEL = "gpt-4-1106-preview"
# Can be higher, but save $$$ with some potential loss in perf
MESSAGE_THRESHOLD = 3_000

# If set, dump chat messages there.
MESSAGE_DIRECTORY = None

# Test code used when running integration tests
# TODO: mock out for integration tests
TESTING = False
TEST_RESPONSE = """
{"id": "chatcmpl-8VpkBh4MOnvETZRZUphRo0QXk9tdN", "object": "chat.completion", "created": 1702597763, "model": "gpt-3.5-turbo-1106", "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hello! How can I assist you today? If you have any questions or need assistance with world-building, character creation, or storytelling, feel free to ask!"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 2074, "completion_tokens": 33, "total_tokens": 2107}, "system_fingerprint": "fp_f3efa6edfc"}
"""


@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def chat_completion_request(messages, tools=None, tool_choice=None, model=GPT_MODEL):
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
        logging.error("Exception: %s", e)
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
        print(
            colored(f"system: {message['content']}\n", role_to_color[message["role"]])
        )
    elif message["role"] == "user":
        print(colored(f"user: {message['content']}\n", role_to_color[message["role"]]))
    elif message["role"] == "assistant" and message.get("tool_calls"):
        print(
            colored(
                f"assistant: {message['tool_calls']}\n", role_to_color[message["role"]]
            )
        )
    elif message["role"] == "assistant":
        print(
            colored(
                f"assistant: {message['content']}\n", role_to_color[message["role"]]
            )
        )
    elif message["role"] == "tool":
        print(
            colored(
                f"function {message['tool_call_id']}: "
                + f"({message['name']}): {message['content']}\n",
                role_to_color[message["role"]],
            )
        )


def print_log(value):
    print(value)
    logging.info(value)


def log_chat_message(messages, assistant_message):
    """
    If enabled, write a timestamped file with messages
    """
    if MESSAGE_DIRECTORY is not None:
        path = os.path.join(MESSAGE_DIRECTORY, "messages")
        if not os.path.exists(path):
            os.makedirs(path)

        out = {"message": messages, "assistant": assistant_message}
        ts = time.time()
        filename = f"message.{ts}.txt"
        path = os.path.join(path, filename)
        with open(path, "w") as f:
            f.write(json.dumps(out, indent=4))
            f.close()


class ChatResponse(pydantic.BaseModel):
    id: str
    done: bool
    user: str = ""
    reply: str = ""
    updates: str = ""
    event: str = ""
    tool_call: str = ""
    status: str = "ok"


class ChatTokens(pydantic.BaseModel):
    prompt_tokens: int = 0
    complete_tokens: int = 0
    total_tokens: int = 0


class ChatState(pydantic.BaseModel):
    # ID for in process message
    msg_id: str = ""
    
    # Number of function calls made
    call_count: int = 0
    
    # Total number function calls allowed
    call_limit: int = 0
    
    # True if next action is a tool call
    tool_call_pending: bool = False
    # If tool_call_pending, this is the index of the call in the message
    # Supports multiple tool calls per assistant response
    tool_call_index: int = 0

    # Current doc id for archiving messages
    archive_doc_id: str = ""
    
    # Context passed to the chat_functions (world_id, etc)
    context: str = "{}"
    
    # Message history - list of groups (each a list) of messages
    messages: str = "[]"
    
    # Token counts
    tokens: ChatTokens = ChatTokens()


class ChatSession:
    def __init__(self, chatFunctions=None):
        self.msg_id = ""
        self.call_count = 0
        self.call_limit = 0
        self.tool_call_pending = False
        self.tool_call_index = 0
        if chatFunctions is None:
            self.chatFunctions = chat_functions.BaseChatFunctions()
        else:
            self.chatFunctions = chatFunctions
        self.prompt_tokens = 0
        self.complete_tokens = 0
        self.total_tokens = 0
        self.enc = tiktoken.encoding_for_model(GPT_MODEL)
        self.history = message_records.MessageRecords()
        self.archive_doc_id = ""

    def load(self, model_str):
        state = ChatState(**json.loads(model_str))
        self.history = message_records.MessageRecords()
        self.history.load_history(json.loads(state.messages))
        self.chatFunctions.setProperties(json.loads(state.context))

        self.msg_id = state.msg_id
        self.tool_call_pending = state.tool_call_pending
        self.tool_call_index = state.tool_call_index
        self.call_count = state.call_count
        self.call_limit = state.call_limit
        self.prompt_tokens = state.tokens.prompt_tokens
        self.complete_tokens == state.tokens.complete_tokens
        self.total_tokens == state.tokens.total_tokens
        self.archive_doc_id = state.archive_doc_id

    def save(self):
        state = ChatState()
        state.msg_id = self.msg_id
        state.tool_call_pending = self.tool_call_pending
        state.tool_call_index = self.tool_call_index
        state.call_count = self.call_count
        state.call_limit = self.call_limit
        state.tool_call_index = self.tool_call_index
        state.tokens.prompt_tokens = self.prompt_tokens
        state.tokens.complete_tokens = self.complete_tokens
        state.tokens.total_tokens = self.total_tokens
        state.messages = json.dumps(self.history.dump_history())
        state.context = json.dumps(self.chatFunctions.getProperties())
        state.archive_doc_id = self.archive_doc_id
        model_str = json.dumps(state.model_dump())
        return model_str

    def track_tokens(self, db, prompt, complete, total):
        self.prompt_tokens += prompt
        self.complete_tokens += complete
        self.total_tokens += total
        self.chatFunctions.track_tokens(db, prompt, complete, total)
        logging.info("prompt: %s, complete: %s, total: %s",
                     prompt, complete, total)

    def execute_function_call(self, db, function_name, function_args):
        return self.chatFunctions.execute_function_call(
            db, function_name, function_args
        )

    def BuildMessages(self, history, instructions):
        """
        Take a MessageRecords instance
        Return a list of messages that fit context size
        """
        messages = []
        history.clearIncluded()

        history.setInitSystemMessage(
            {
                "role": "system",
                "content": instructions,
            }
        )

        functions = self.chatFunctions.get_available_tools()
        history.setFunctions(self.enc, functions)

        thread_size = 0
        for message_set in reversed(history.message_sets()):
            new_size = history.getThreadTokenCount(
                self.enc
            ) + message_set.getTokenCount(self.enc)
            if new_size < MESSAGE_THRESHOLD:
                message_set.setIncluded()
                thread_size = new_size
            else:
                break

        history.addIncludedMessagesToList(messages)
        logging.info("calc thread size %s",  thread_size)
        return messages
    
    def getMessageContent(self, message_set):
        content = message_set.getMessageContent()
        return content

    def chat_history(self):
        messages = []
        for message_set in self.history.message_sets():
            # Don't include messages that didn't finish
            # (Should only happen on the most recent message)
            if message_set.wasCompleted():
                messages.append(self.getMessageContent(message_set))
        return {"messages": messages}

    def chat_exchange(
        self,
        db,
        user: typing.Union[str, None] = None,
        system: typing.Union[str, None] = None,
        tool_choice: typing.Union[str, None] = None,
        call_limit=11,
    ) -> ChatResponse:
        """
        Loop through steps in a chat exchange.
        - start
        - continue with tools calls and following chats
        """
        result = self.chat_start(db, user=user, system=system, tool_name=tool_choice)
        self.call_limit = call_limit
        msg_id = result.id
        while not result.done and self.call_count <= call_limit:
            result = self.chat_continue(db, msg_id)
        return result

    def chat_start(
        self,
        db,
        user: typing.Union[str, None] = None,
        system: typing.Union[str, None] = None,
        tool_name: typing.Union[str, None] = None,
    ) -> ChatResponse:
        """
        Initiate a new chat
        """
        self.msg_id = os.urandom(8).hex()
        self.call_count = 0
        self.call_limit = 10
        self.tool_call_pending = False
        self.tool_call_index = 0
        self.chatFunctions.clearChanges()

        self.history.startNewMessageSet()

        if system is not None:
            self.history.addMessage({"role": "system", "content": system})
        if user is not None:
            self.history.addMessage({"role": "user", "content": user})

        # First run a chat completion, may be the last operation
        return self.chat_message(db, tool_name)

    def chat_message(
        self, db, tool_name: typing.Union[str, None] = None
    ) -> ChatResponse:
        """
        Process a chat message completion call.
        - May result in a complete exchange
        - May result in tools calls to be done
        """
        self.call_count += 1
        if self.call_count > 8:
            print(f"too many calls: {self.call_count}")
            result = ChatResponse(id=self.msg_id, done=True)
            result.status = "error"
            return result

        instructions = self.chatFunctions.get_instructions(db)
        messages = self.BuildMessages(self.history, instructions)
        print_log(f"[{self.call_count}]: Chat completion call...")
        # Limit tools call to 7
        if self.call_count < 8:
            tools = self.chatFunctions.get_available_tools()
        else:
            tools = None

        if tool_name is not None:
            logging.info("ChatEx called with tool: %s", tool_name)
            tool_choice = {"type": "function", "function": {"name": tool_name}}
        else:
            tool_choice = None

        # Make completion request call with the messages we have
        # selected from the message history and potentially
        # available tools and specified tool choice.
        # print(json.dumps(messages))
        response = chat_completion_request(
            messages, tools=tools, tool_choice=tool_choice
        )
        logging.info("Response: %s", json.dumps(response))

        # Clear tool choice, only force a tool call on the first request.
        tool_name = None

        # Check for an error
        if response.get("usage") is not None:
            usage = response["usage"]
            self.track_tokens(
                db,
                usage["prompt_tokens"],
                usage["completion_tokens"],
                usage["total_tokens"],
            )
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
            result = ChatResponse(id=self.msg_id, done=True)
            result.status = "error"
            return result

        self.history.addMessage(assistant_message)
        tool_calls = assistant_message.get("tool_calls")
        if tool_calls:
            # Make requested calls to tools.
            self.tool_call_index = 0
            self.tool_call_pending = True

        # Build result
        content = self.getMessageContent(self.history.current_message_set())
        result = ChatResponse(id=self.msg_id, done=tool_calls is None)
        result.user = content["user"]
        result.reply = content["assistant"]
        result.updates = content["updates"]
        result.event = content["system"]

        tool_call = self.get_current_tool_call()
        if tool_call is not None:
            result.tool_call = tool_call["function"]["name"]
        return result

    def chat_continue(self, db, msg_id):
        """
        Perform the next step in a chat exchange
        May either call an additional chat completion or make a tools call
        """
        # Completion or Tool Call
        if not self.tool_call_pending:
            return self.chat_message(db)

        # Make a tools call
        status_text = None
        # Set up tools_calls
        tool_call = self.get_current_tool_call()
        self.tool_call_index = self.tool_call_index + 1
        if self.tool_call_index >= self.get_tool_call_count():
            self.tool_call_pending = False

        function_name = tool_call["function"]["name"]
        function_args = json.loads(tool_call["function"]["arguments"])
        print_log(f"function call: {function_name}")
        function_response = self.execute_function_call(db, function_name, function_args)
        logging.info("function call result: %s" % str(function_response))
        # Handle 2 different formats of return values
        content = None
        if isinstance(function_response, dict):
            content = function_response.get("response")
            status_text = function_response.get("text")
        if content is None:
            content = function_response

        self.history.addMessage(
            {
                "tool_call_id": tool_call["id"],
                "role": "tool",
                "name": function_name,
                "content": json.dumps(content),
            },
            status_text,
        )

        # Build result
        done = False
        # Can be done if no more tool alls AND we have met the chat call limt
        if not self.tool_call_pending and self.call_count < self.call_limit:
            done = True

        content = self.getMessageContent(self.history.current_message_set())
        result = ChatResponse(id=self.msg_id, done=False)
        result.user = content["user"]
        result.reply = content["assistant"]
        result.updates = content["updates"]
        result.event = content["system"]

        tool_call = self.get_current_tool_call()
        if tool_call is not None:
            result.tool_call = tool_call["function"]["name"]
        return result

    def get_current_tool_call(self):
        if not self.tool_call_pending:
            return None

        tool_message = self.history.current_message_set().getToolRequestMessage()
        tool_calls = tool_message.get("tool_calls")
        tool_call = tool_calls[self.tool_call_index]
        return tool_call

    def get_tool_call_count(self):
        tool_message = self.history.current_message_set().getToolRequestMessage()
        return len(tool_message.get("tool_calls"))
