#!/usr/bin/env python3
"""
Dump the contents of the database
"""

import datetime
import os
import json

from . import elements
from . import chat_functions

def list_images(parent_id):
  print("Listing images...")
  image_list = elements.listImages(chat_functions.get_db(), parent_id)
  for entry in image_list:
    print("Image(%s) filename:%s, prompt: %s" %
          (entry["id"], entry["filename"], entry["prompt"]))

dir = os.path.split(os.path.split(__file__)[0])[0]
dir = os.path.join(dir, 'instance')
print(f"dir: {dir}")
chat_functions.init_config(dir, "worldai.sqlite")

print("Loading worlds...")
worlds = elements.listWorlds(chat_functions.get_db())
print("%d worlds listed" % len(worlds))

for (entry) in worlds:
  id = entry["id"]
  name = entry["name"]
  print(f"World({id}): {name}")
  
  world = elements.loadWorld(chat_functions.get_db(), id)
  print(world.getPropertiesJSON())
  list_images(world.id)

  print("Loading characters...")
  characters = elements.listCharacters(chat_functions.get_db(), world.id)
  for (char_entry) in characters:
    id = char_entry["id"]
    name = char_entry["name"]
    print(f"Character({id}): {name}")

    character = elements.loadCharacter(chat_functions.get_db(), id)
    print(character.getPropertiesJSON())
    list_images(character.id)
    
  print("\n\n")
  
