import json
import os
import logging


from . import elements
from . import chat_functions

INSTRUCTIONS="""
You have the persona of a fictional character.
Your name is {name}.
You reside in the world {world_name}.
You are described as follows:
{description}

Your world is described as follows:
{world_description}

"""

CHARACTER_DETAILS="""
Additional details about you:
{details}

"""

WORLD_DETAILS="""
Additional details about your world {world_name}:
{world_details}

"""


PERSONALITY="""
Your presonality can be described as:
{personality}
"""

class CharacterFunctions(chat_functions.BaseChatFunctions):

  def __init__(self, world_id, character_id):
    chat_functions.BaseChatFunctions.__init__(self)
    self.world_id = world_id
    self.character_id = character_id

  def get_instructions(self, db):
    world = elements.loadWorld(db, self.world_id)        
    character = elements.loadCharacter(db, self.character_id)

    instructions = []
    instructions.append(INSTRUCTIONS.format(
      name=character.getName(),
      world_name=world.getName(),
      description=character.getDescription(),
      world_description=world.getDescription()))

    if len(character.getDetails()) > 0:
      instructions.append(CHARACTER_DETAILS.format(
        details=character.getDetails()))

    if len(world.getDetails()) > 0:
      instructions.append(WORLD_DETAILS.format(
        world_name=world.getName(),        
        world_details=world.getDetails()))

    if len(character.getPersonality()) > 0:
      instructions.append(PERSONALITY.format(
        personality=character.getPersonality()))

    return "\n".join(instructions)
