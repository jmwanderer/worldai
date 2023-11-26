import json

functions = [
    {
        "name": "start_new_hangman_game",
        "description": "Start a new game",
        "parameters": {
            "type": "object",
            "properties": {
                "word_size": {
                    "type": "integer",
                    "description": "Size of word to guess",
                },
                "max_wrong_guesses": {
                    "type": "integer",
                    "description": "The number of wrong guesses allowed.",
                },
            },
            "required": ["word_size", "max_wrong_guesses"],
        },
        "returns": {
          "type": "string",
          "description": "The word to guess",
        },
    },
    {
        "name": "record_guess",
        "description": "Record a guess made by the player.",
        "parameters": {
            "type": "object",
            "properties": {
                "letter": {
                    "type": "string",
                    "description": "The letter guessed by the player.",
                },
            },
            "required": ["letter"]
        },
        "returns": {
          "type": "object",
          "properties": {
            "found" : {
              "type": "boolean",
              "description": "Was the letter found in the word",
            },
            "visible_word" : {
              "type": "string",
              "description": "The current view of the word.",
            },
            "word" : {
              "type": "string",
              "description": "The secret word.",
            },
            "remaining_guesses" : {
              "type": "integer",
              "description": "The number of remaining guesses for the player",
            },
            "status" : {
              "type": "string",
              "enum": ["won", "lost", "inprogress"], 
              "description": "Current sate of the game",
            },
          },
        },
    },
]            


def execute_function_call(function_call):
  if function_call["name"] == "start_new_hangman_game":
    arguments = json.loads(function_call['arguments'])
    return "queen"

  if function_call["name"] == "record_guess":
  
    content = { "found" : False,
                "visible_word" : "__x++",
                "word" : "a new word",                
                "remaining_guesses" : 4,
                "status" : 1 }
    return json.dumps(content)

  return ""
