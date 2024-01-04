import json

"""
Manages and curates the chat history.
Supports building a message history for a target size.
Supports ensuring required tool calls / information gets populated.
"""



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
      # json format of response
      self.response_messages = []
      # text status - functions can return descriptions
      self.response_texts = []      

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
    results = []
    for entry in self.tool_messages:
      content = entry.request_message.get("content")
      # Note tool messages can also have content
      if content is not None:
        results.append(content)
    if self.response_message is not None:
      results.append(self.response_message["content"])
    return "\n\n".join(results)

  def getStatusText(self):
    # Return any status text to present to the user.
    results = []
    for entry in self.tool_messages:
      results.extend(entry.response_texts)
    return ", ".join(results)

  def getMessageContent(self):
    # Return a JSON record of full message content
    # that can be returned to the client.
    return { "user": self.getRequestContent(),
             "assistant": self.getResponseContent(),
             "updates": self.getStatusText() };
  
  def addToolRequestMessage(self, enc, message):
    record = MessageSetRecord.ToolRequestMessage()
    record.request_message = message
    self.tool_messages.append(record)
    self._updateTokenCount(enc, message)    

  def addToolResponseMessage(self, enc, message, text):
    record = self.tool_messages[-1]
    record.response_messages.append(message)
    if text is not None:
      record.response_texts.append(text)
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
    
  def addToolResponseMessage(self, enc, message, text=None):
    if self.current_message is not None:
      self.current_message.addToolResponseMessage(enc, message, text)

  def addResponseMessage(self, enc, message):
    if self.current_message is not None:
      self.current_message.setResponseMessage(enc, message)

  def message_sets(self):
    return self.message_history

  def current_message_set(self):
    return self.current_message

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
    
