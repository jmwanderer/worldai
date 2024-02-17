import json
import os
import tempfile

import pytest
import tiktoken
import worldai.chat
import worldai.db_access
import worldai.server

"""
Test fixtures for WorldAI
- application
- web client
- CLI client
"""


@pytest.fixture()
def app():
    instance_path = tempfile.TemporaryDirectory()

    test_config = {
        "TESTING": True,
        "OPENAI_API_KEY": "dummy key",
    }
    app = worldai.server.create_app(
        instance_path=instance_path.name, test_config=test_config
    )

    # Populate DB with test data
    path = os.path.join(os.path.dirname(__file__), "test_data.sql")
    db = worldai.db_access.open_db()
    with open(path) as f:
        db.executescript(f.read())
    db.close()
    # Mock out chat calls
    chatmock = ChatMockUtil()
    chatmock.setUp()

    yield app

    instance_path.cleanup()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.text_cli_runner()


class ChatMockUtil:

    def setUp(self):
        # Stub out the user input, completion request, and exec fuc routines
        self.max_token_count = 0
        self.encoder = tiktoken.encoding_for_model(worldai.chat.GPT_MODEL)
        os.environ["OPENAI_API_KEY"] = "dummy key"

        def chat_completion_request(messages, tools=None, tool_choice=None):
            tokenCount = self.calcTokens(messages)
            self.max_token_count = max(tokenCount, self.max_token_count)
            print(f"********** token count: {tokenCount}, max: {self.max_token_count}")
            return self.getCompletionResponse(response_msg)

        # Key item to mock out
        worldai.chat.chat_completion_request = chat_completion_request

    def getCompletionResponse(self, msg):
        completion_response = {
            "choices": [{"index": 0, "message": msg, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": 200,
                "completion_tokens": 50,
                "total_tokens": 250,
            },
        }
        return completion_response

    def calcTokens(self, messages):
        total = 0
        for message in messages:
            total += len(self.encoder.encode(json.dumps(message)))
            return total


response_msg = {
    "role": "assistant",
    "content": "Hello! It looks like you're interested in creating or exploring fictional worlds and characters. How can I assist you today?",
}
