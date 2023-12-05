from worldai import chat

import unittest
import unittest.mock
import tempfile
import json
import os
import tiktoken

def getSystemMessage():
  return { "role": "system", "content": "You are a friendly assistant."}

def getUserMessage():
  return { "role": "user", "content": "How do I get to San Jose?"}

def getAssistantMessage():
  return { "role": "assistant", "content": "South on 101"}    

def getToolRequestMessage():
  return { 'role': 'assistant', 'content': None,
           'tool_calls': [{
             'id': 'call_XYZX',
             'type': 'function',
             'function': {
               'name': 'lookup_route',
               'arguments': '{\n "start": "Palo Alto",\n "end": "San Jose"\n}'
             }
           }]
          }

def getToolResponseMessage():
  return { 'role': 'tool',
           'tool_call_id': 'call_XYZX',
           'name': 'lookup_route',
           'content': 'South on 101' }

class RecordsTestCase(unittest.TestCase):
  def testMessageRecords(self):
    enc = tiktoken.encoding_for_model(chat.GPT_MODEL)    
    records = chat.MessageRecords()
    records.setSystemMessage(getSystemMessage())
    records.addRequestMessage(enc, getUserMessage())
    records.addResponseMessage(enc, getAssistantMessage())
    # Just system message included
    self.assertEqual(records.getThreadTokenCount(enc), 13)

    records.message_sets()[0].setIncluded()
    self.assertNotEqual(records.getThreadTokenCount(enc), 0)

    records.clearIncluded()
    self.assertEqual(records.getThreadTokenCount(enc), 13)    

    records.addRequestMessage(enc, getUserMessage())
    records.addToolRequestMessage(enc, getToolRequestMessage())
    records.addToolResponseMessage(enc, getToolResponseMessage())
    records.addResponseMessage(enc, getAssistantMessage())    

    message_set = records.message_sets()[1]
    self.assertTrue(message_set.hasToolCall("lookup_route", {}))
    self.assertFalse(message_set.hasToolCall("lookup_weather", {}))

    messages = []
    records.addIncludedMessagesToList(messages)
    self.assertEqual(len(messages), 1)

    messages = []    
    records.message_sets()[0].setIncluded()
    records.message_sets()[1].setIncluded()
    records.addIncludedMessagesToList(messages)
    self.assertEqual(len(messages), 7)

    print(records.jsonString())


class ExtendedRecordsTestCase(unittest.TestCase):

  # Encoder that only returns 1 element
  class Encode:
    def encode(self, my_input):
      return ["1"]
    
  def testMessageRecords(self):
    enc = ExtendedRecordsTestCase.Encode()
    records = chat.MessageRecords()
    records.setSystemMessage(getSystemMessage())
    records.addRequestMessage(enc, getUserMessage())

    # Repeated tool calls
    # Call 1
    records.addToolRequestMessage(enc, getToolRequestMessage())
    records.addToolResponseMessage(enc, getToolResponseMessage())
    records.addToolResponseMessage(enc, getToolResponseMessage())
    records.addToolResponseMessage(enc, getToolResponseMessage())

    # Call 2
    records.addToolRequestMessage(enc, getToolRequestMessage())
    records.addToolResponseMessage(enc, getToolResponseMessage())
    records.addToolResponseMessage(enc, getToolResponseMessage())

    # Call 3
    records.addToolRequestMessage(enc, getToolRequestMessage())
    records.addToolResponseMessage(enc, getToolResponseMessage())

    # Final response
    records.addResponseMessage(enc, getAssistantMessage())

    # Include all
    for message_set in records.message_sets():
      message_set.setIncluded()

    # Count number of size 1 messages
    self.assertEqual(records.getThreadTokenCount(enc), 86)

    

class SaveLoadTestCase(unittest.TestCase):

  def setUp(self):
    self.user_dir = tempfile.TemporaryDirectory()

  def tearDown(self):
    self.user_dir.cleanup()

  def testLoadSave(self):
    path = os.path.join(self.user_dir.name, "1")
    session = chat.ChatSession.loadChatSession(path)
    self.assertIsNotNone(session)

    session.saveChatSession()

    session = chat.ChatSession.loadChatSession(path)
    self.assertIsNotNone(session)

    

def getCompletionResponse(msg):
  completion_response = {
      "choices": [ {
        "index": 0,
        "message":  msg,
        "finish_reason": "stop"
      }],
      "usage": {
        "prompt_tokens": 200,
        "completion_tokens": 50,
        "total_tokens": 250
        }
      }
  return completion_response

    
class BasicChatTestCase(unittest.TestCase):

  def setUp(self):
    # Stub out the user input, completion request, and exec fuc routines
    self.request_count = 0

    def chat_completion_request(messages, tools=None, tool_choice=None):
      # Return:
      # 1: assistant response
      # 2: tool request
      # 3: assistant response
      self.request_count += 1
      print("get completion request")
      if self.request_count == 1:
        return getCompletionResponse(getAssistantMessage())
      if self.request_count == 2:
        return getCompletionResponse(getToolRequestMessage())
      return getCompletionResponse(getAssistantMessage())      

    def get_user_input():
      # Return:
      # 1: "hello"
      # 2: EOF exception
      print("get user input")
      if self.request_count == 0:
        return "Hello"
      raise EOFError()

    def get_function_result(dummy_self, db, name, args):
      # Note: dummy_self is the ChatSession instance      
      return getToolResponseMessage()

    def track_tokens(dummy_self, db, prompt, complete, total):
      # Note: dummy_self is the ChatSession instance      
      pass
    
    chat.chat_completion_request = chat_completion_request
    chat.get_user_input = get_user_input
    chat.ChatSession.execute_function_call = get_function_result
    chat.ChatSession.track_tokens = track_tokens

  def testChatLoop(self):
    chat.chat_loop()


class ExtendedChatTestCase(unittest.TestCase):

  def setUp(self):
    # Stub out the user input, completion request, and exec fuc routines
    self.msg_index = 0
    self.max_token_count = 0
    self.encoder = tiktoken.encoding_for_model(chat.GPT_MODEL)        

    def get_user_input():
      if self.msg_index == len(msg_thread):
        raise EOFError()      
      msg = msg_thread[self.msg_index]
      self.msg_index += 1
      self.assertEqual(msg.get("role"), "user")
      return msg.get("content")

    def chat_completion_request(messages, tools=None, tool_choice=None):
      tokenCount = self.calcTokens(messages)
      self.max_token_count = max(tokenCount, self.max_token_count)
      print(f"********** token count: {tokenCount}, max: {self.max_token_count}")
      msg_response = msg_thread[self.msg_index]
      self.msg_index += 1
      self.assertEqual(msg_response.get("role"), "assistant")
      return getCompletionResponse(msg_response)

    def get_function_result(dummy_self, db, name, args):
      # Note: dummy_self is the ChatSession instance      
      msg_result = msg_thread[self.msg_index]
      self.msg_index += 1
      self.assertEqual(msg_result.get("role"), "tool")
      return msg_result

    def track_tokens(dummy_self, db, prompt, complete, total):
      # Note: dummy_self is the ChatSession instance      
      pass

    chat.chat_completion_request = chat_completion_request
    chat.get_user_input = get_user_input
    chat.ChatSession.execute_function_call = get_function_result
    chat.ChatSession.track_tokens = track_tokens

  def calcTokens(self, messages):
    total = 0
    for message in messages:
      total += len(self.encoder.encode(json.dumps(message)))
      return total

  def testSimpleChatLoop(self):
    # No buffer management needed
    chat.MESSAGE_THRESHOLD=6_000
    chat.chat_loop()
    self.assertLess(self.max_token_count, chat.MESSAGE_THRESHOLD)
    

  def testComplexChatLoop(self):
    # No buffer management needed
    chat.chat_loop()
    self.assertLess(self.max_token_count, chat.MESSAGE_THRESHOLD)    
    

msg_thread = [
  {"role": "user", "content": "hi"},
  {"role": "assistant", "content": "Hello! It looks like you're interested in creating or exploring fictional worlds and characters. How can I assist you today?"},
  {"role": "user", "content": "existing world"},
  {"role": "assistant", "content": None, "tool_calls": [{"id": "call_awrKAQUyuQ2CpaFrAl6qHqyx", "type": "function", "function": {"name": "ListWorlds", "arguments": "{}"}}]},
  {"tool_call_id": "call_awrKAQUyuQ2CpaFrAl6qHqyx", "role": "tool", "name": "ListWorlds", "content": "[{\"id\": \"id8316b7c4\", \"name\": \"Starkwards\"}, {\"id\": \"ida1ad7f2c\", \"name\": \"Witcher's Realm\"}, {\"id\": \"ided86d740\", \"name\": \"Wanderer World\"}, {\"id\": \"ida00fd73d\", \"name\": \"Kanazawa World\"}, {\"id\": \"idba79d8ef\", \"name\": \"StarkWorlds\"}]"},
  {"role": "assistant", "content": "It looks like we have several existing worlds to choose from:\n\n1. Starkwards\n2. Witcher's Realm\n3. Wanderer World\n4. Kanazawa World\n5. StarkWorlds\n\nWhich world would you like to explore or make changes to? If you'd like to create a new world, feel free to provide a name for the new world."},
  {"role": "user", "content": "witchers please"},
  {"role": "assistant", "content": None, "tool_calls": [{"id": "call_BYRjKJPnig6KMYug2p6aR2hX", "type": "function", "function": {"name": "ReadWorld", "arguments": "{\"id\":\"ida1ad7f2c\"}"}}]},
  {"tool_call_id": "call_BYRjKJPnig6KMYug2p6aR2hX", "role": "tool", "name": "ReadWorld", "content": "{\"id\": \"ida1ad7f2c\", \"name\": \"Witcher's Realm\", \"description\": \"Witcher's Realm is a dark fantasy world filled with monsters, magic, and political intrigue. It is a land plagued by war and strife, where witchers, powerful monster hunters, roam the continent. The world is beautifully detailed and features diverse landscapes, ancient ruins, haunted forests, and bustling cities. Prepare to embark on a thrilling adventure where your choices and actions will have far-reaching consequences.\", \"details\": \"Witcher's Realm is a dark fantasy world filled with monsters, magic, and political intrigue. It is a land plagued by war and strife, where witchers, powerful monster hunters, roam the continent. The world is beautifully detailed and features diverse landscapes, ancient ruins, haunted forests, and bustling cities. Prepare to embark on a thrilling adventure where your choices and actions will have far-reaching consequences.\\n\\nMain Characters:\\n\\n1. Geralt of Rivia: The protagonist and a skilled monster hunter known as a witcher. Geralt is stoic, skilled in combat, and has a strong sense of morality.\\n\\n2. Yennefer of Vengerberg: A powerful sorceress who becomes a love interest for Geralt. Yennefer is cunning, ambitious, and possesses immense magical abilities.\\n\\n3. Ciri: A young princess with a mysterious and powerful lineage. Ciri becomes an important figure in the war-torn world and is pursued by various factions who seek to control her abilities.\\n\\n4. Triss Merigold: Another sorceress and friend of Geralt. Triss is compassionate and skilled in healing magic. She often assists Geralt and serves as a source of support and advice.\\n\\nKey Sites:\\n\\n1. Kaer Morhen: The ancient fortress where witchers are trained and live. It is a secluded, fortified stronghold nestled amidst the mountains. Kaer Morhen serves as a hub for witcher activities and training.\\n\\n2. Novigrad: One of the largest cities in Witcher's Realm, Novigrad is a bustling metropolis known for its diverse population and vibrant markets. It is a hub of trade, politics, and intrigue.\\n\\n3. Velen: A war-torn, desolate region with haunted forests and ancient burial mounds. Velen is plagued by monsters and is home to various factions vying for power.\\n\\n4. Skellige Isles: A cluster of rugged islands inhabited by fierce warrior clans. The Skellige Isles are known for their naval prowess, treacherous seas, and strong Viking-like traditions.\"}"},
  {"role": "assistant", "content": "\"Witcher's Realm\" is a dark fantasy world filled with monsters, magic, and political intrigue. It is a land plagued by war and strife, where witchers, powerful monster hunters, roam the continent. The world features diverse landscapes, ancient ruins, haunted forests, and bustling cities. Your choices and actions will have far-reaching consequences in this realm.\n\nThe main characters in Witcher's Realm include:\n1. Geralt of Rivia: The protagonist and a skilled witcher, known for his stoicism, combat skills, and strong sense of morality.\n2. Yennefer of Vengerberg: A powerful sorceress, cunning and ambitious, with immense magical abilities. She becomes a love interest for Geralt.\n3. Ciri: A young princess with a mysterious and powerful lineage, pursued by various factions due to her abilities and influence.\n4. Triss Merigold: A compassionate sorceress and friend of Geralt, skilled in healing magic, offering support and advice.\n\nKey sites within Witcher's Realm:\n1. Kaer Morhen: An ancient fortress where witchers are trained and reside, nestled amidst the mountains and functioning as a hub for witcher activities and training.\n2. Novigrad: A bustling metropolis known for its diverse population, vibrant markets, and serving as a hub for trade, politics, and intrigue.\n3. Velen: A war-torn, desolate region with haunted forests, ancient burial mounds, and various factions vying for power. It is plagued by monsters.\n4. Skellige Isles: A cluster of rugged islands inhabited by fierce warrior clans, known for their naval prowess, treacherous seas, and strong Viking-like traditions.\n\nWould you like to make any changes or add more details to the world \"Witcher's Realm,\" or would you like to focus on developing new characters within this world?"},
  {"role": "user", "content": "add a new character"},
  {"role": "assistant", "content": None, "tool_calls": [{"id": "call_U0whL63PYhg1tAmCZY2YjJJJ", "type": "function", "function": {"name": "ChangeState", "arguments": "{\"state\":\"State_Edit_Characters\"}"}}]},
  {"tool_call_id": "call_U0whL63PYhg1tAmCZY2YjJJJ", "role": "tool", "name": "ChangeState", "content": "state changed"},
  {"role": "assistant", "content": "Great! We're now in the \"State_Edit_Characters\" mode. Please provide details for the new character you'd like to add to the \"Witcher's Realm.\" This could include the character's name, backstory, abilities, motivations, and any other relevant information that will help bring the character to life within this dark fantasy world. Feel free to be as creative as you like!"},
  {"role": "user", "content": "add a king, think of a new name"},
  {"role": "assistant", "content": None, "tool_calls": [{"id": "call_l19y0ADWtpUlyO3wG1NeNri9", "type": "function", "function": {"name": "CreateCharacter", "arguments": "{\"name\":\"King Emeric van Auldburgh\",\"description\":\"King Emeric van Auldburgh is a respected and influential monarch of one of the key territories in Witcher's Realm. He rules with wisdom and strategic acumen, navigating the treacherous political landscape of the continent and striving to maintain peace amidst the chaos of war and magical enmity.\"}"}}]},
  {"tool_call_id": "call_l19y0ADWtpUlyO3wG1NeNri9", "role": "tool", "name": "CreateCharacter", "content": "\"idf11b1819\""},
  {"role": "assistant", "content": "The character \"King Emeric van Auldburgh\" has been successfully created. King Emeric is described as a respected and influential monarch ruling with wisdom and strategic acumen, navigating the treacherous political landscape of Witcher's Realm to maintain peace amidst the chaos of war and magical enmity.\n\nIs there anything else you'd like to add or modify about King Emeric van Auldburgh, or would you like to create more characters or work on other aspects of the world?"},

  # Insert double tool call here:
  {"role": "user", "content": "list characters"},
  {"role": "assistant", "content": None, "tool_calls": [
    {'id': 'call_zeHJ1afDBYDooGnyzl3ipb1d', 'type': 'function',
     'function': {'name': 'ReadCharacter',
                  'arguments': '{"id": "id53c19c9b"}'}},
    {'id': 'call_CNBZTat24sibg1Jd534QpK9d', 'type':
     'function', 'function': {'name': 'ReadCharacter',
                              'arguments': '{"id": "id85878e64"}'}}
  ]},
  {"tool_call_id": "call_zeHJ1afDBYDooGnyzl3ipb1d", "role": "tool",
   "name": "ReadCharacter",
   "content": "no character id53c19c9b"},
  {"tool_call_id": "call_CNBZTat24sibg1Jd534QpK9d", "role": "tool",
   "name": "ReadCharacter",
   "content": "no character id85878e64"},
  {"role": "assistant", "content": "Uh, yeah, that didn't work. Why did I do that? Nobody knows. What is wrong with listing the characters? Sigh."},
  # Done insert
  
  {"role": "user", "content": "lets add some details for him"},
  {"role": "assistant", "content": None, "tool_calls": [{"id": "call_og7g8qEMIi8suYdS94RTTQuB", "type": "function", "function": {"name": "UpdateCharacter", "arguments": "{\"name\":\"King Emeric van Auldburgh\",\"details\":\"King Emeric van Auldburgh hails from the ancient line of Auldburgh, a lineage known for its resilience and commitment to the welfare of its people. As a ruler, King Emeric prioritizes diplomacy and collaboration, seeking to forge alliances and strengthen the prosperity of his kingdom. However, his peaceful demeanor conceals astute political maneuvering and an acute understanding of the power dynamics at play. His motivations center around ensuring the safety and well-being of his subjects, even in the face of supernatural threats and feuds that plague the realm.\"}"}}]},
  {"tool_call_id": "call_og7g8qEMIi8suYdS94RTTQuB", "role": "tool", "name": "UpdateCharacter", "content": "updated"},
  {"role": "assistant", "content": "Details for King Emeric van Auldburgh have been updated. King Emeric hails from the ancient line of Auldburgh, known for resilience and commitment to the welfare of its people. He prioritizes diplomacy and collaboration, seeks to forge alliances, and is committed to ensuring the safety and well-being of his subjects, even amidst supernatural threats and feuds that plague the realm.\n\nIs there anything else you'd like to do with the characters or the world \"Witcher's Realm\"?"},
  {"role": "user", "content": "create an image"},
  {"role": "assistant", "content": None, "tool_calls": [{"id": "call_K6lVNQQGq7cXXHqV99zcpIS9", "type": "function", "function": {"name": "CreateCharacterImage", "arguments": "{\"id\":\"idf11b1819\",\"prompt\":\"King Emeric van Auldburgh, a wise and influential monarch, surveying his kingdom with a watchful gaze as he navigates the treacherous political landscape of Witcher's Realm.\"}"}}]},
  {"tool_call_id": "call_K6lVNQQGq7cXXHqV99zcpIS9", "role": "tool", "name": "CreateCharacterImage", "content": "Image creation complete"},
  {"role": "assistant", "content": "The image for King Emeric van Auldburgh has been successfully created, capturing the essence of his wise and influential nature as he navigates the treacherous political landscape of Witcher's Realm.\n\nIs there anything else you'd like to work on in \"Witcher's Realm,\" such as creating more characters, refining existing ones, or focusing on the world details?"}]
    
if __name__ ==  '__main__':
  unittest.main()
    

