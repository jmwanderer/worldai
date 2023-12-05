import os
import os.path
import pathlib
import time
import functools
import io
import flask
from flask import Flask
from flask import request
from flask import Blueprint, g, current_app, session
from werkzeug.middleware.proxy_fix import ProxyFix
import werkzeug.utils
import logging
import click
import openai

from . import db_access
from . import elements
from . import chat
from . import chat_functions


def create_app(instance_path=None):
  if instance_path is None:
    app = Flask(__name__, instance_relative_config=True)
  else:
    app = Flask(__name__, instance_relative_config=True,
                instance_path=instance_path)
  app.config.from_mapping(
    SECRET_KEY='DEV',
    TEST=False,    
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY'),    
    DATABASE=os.path.join(app.instance_path, 'worldai.sqlite'),    
  )
  app.config.from_prefixed_env()
  app.config.from_pyfile('config.py', silent=True)

  # Configure logging
  BASE_DIR = os.getcwd()
  log_file_name = os.path.join(BASE_DIR, 'log-serve.txt')
  FORMAT = '%(asctime)s:%(levelname)s:%(name)s:%(message)s'
  logging.basicConfig(filename=log_file_name,
                      level=logging.INFO,
                      format=FORMAT,)
  db_access.init_config(app.config['DATABASE'])
  openai.api_key = app.config['OPENAI_API_KEY']
  
  logging.info("Starting worldai.server: %s", __name__)
  
  # If so configured, setup for running behind a reverse proxy.
  if app.config.get('PROXY_CONFIG'):
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1,
                            x_host=1, x_prefix=1)
    logging.info("set proxy fix")

  try:
    logging.info("instance path = %s", app.instance_path)
    os.makedirs(app.instance_path)
  except OSError as err:
    pass
  chat_functions.IMAGE_DIRECTORY = app.instance_path
  
  app.register_blueprint(bp)

  @app.errorhandler(Exception)
  def handle_exception(e):
    logging.exception("Internal error")
    return e
  return app


def get_db():
  if 'db' not in g:
    g.db = db_access.open_db()
  return g.db

def close_db(e=None):
  db = g.pop('db', None)
  if db is not None:
    db.close()


bp = Blueprint('worldai', __name__, cli_group=None)

@bp.cli.command('delete-image')
@click.argument('id')
def delete_image(id):
  """Delete an image."""
  image = elements.getImage(get_db(), id)
  if image is not None:
    elements.deleteImage(get_db(), current_app.instance_path, id)
    click.echo('Deleted image [%s] %s.' % (image.id, image.getName()))
  else:
    click.echo(f'Error, no such image id:{id}')

@bp.cli.command('delete-character')
@click.argument('id')
def delete_character(id):
  """Delete a character and associated images."""
  character = elements.loadCharacter(get_db(), id)
  if character is not None:
    elements.deleteCharacter(get_db(), current_app.instance_path, id)
    click.echo('Deleted character [%s] %s.' % (character.id,
                                               character.getName()))
  else:
    click.echo(f'Error, no such character id:{id}')


def list_images(parent_id):
  print("Listing images...")
  image_list = elements.listImages(get_db(), parent_id)
  for entry in image_list:
    print("Image(%s) filename:%s, prompt: %s" %
          (entry["id"], entry["filename"], entry["prompt"]))
    

@bp.cli.command('dump-worlds')
def dump_worlds():
  """Dump the contents of the world DB."""
  print("Loading worlds...")
  worlds = elements.listWorlds(get_db())
  print("%d worlds listed" % len(worlds))

  for (entry) in worlds:
    id = entry["id"]
    name = entry["name"]
    print(f"World({id}): {name}")
  
    world = elements.loadWorld(get_db(), id)
    print(world.getPropertiesJSON())
    list_images(world.id)

    print("Loading characters...")
    characters = elements.listCharacters(get_db(), world.id)
    for (char_entry) in characters:
      id = char_entry["id"]
      name = char_entry["name"]
      print(f"Character({id}): {name}")

      character = elements.loadCharacter(get_db(), id)
      print(character.getPropertiesJSON())
      list_images(character.id)
    
  print("\n\n")
    

@bp.route('/view', methods=["GET"])
def view():
  """
  Top level logo screen
  """
  return flask.render_template("top.html")
  
@bp.route('/view/worlds', methods=["GET"])
def list_worlds():
  """
  List Worlds
  """
  world_list = []
  worlds = elements.listWorlds(get_db())
  for (entry) in worlds:
    id = entry["id"]
    world = elements.loadWorld(get_db(), id)
    world_list.append((id, world.getName(), world.getDescription()))

  return flask.render_template("list_worlds.html", world_list=world_list)

@bp.route('/view/world/<id>', methods=["GET"])
def view_world(id):
  """
  View a world
  """
  world = elements.loadWorld(get_db(), id)
  if world == None:
    return "World not found", 400

  characters = elements.listCharacters(get_db(), world.id)
  char_list = []
  for entry in characters:
    char_id = entry["id"]
    char_name = entry["name"]
    character = elements.loadCharacter(get_db(), char_id)    
    char_list.append((char_id, char_name, character.getDescription()))

  return flask.render_template("view_world.html", world=world,
                               character_list=char_list)

@bp.route('/view/worlds/<wid>/characters/<cid>', methods=["GET"])
def view_character(wid, cid):
  """
  View a character
  """
  world = elements.loadWorld(get_db(), wid)
  if world == None:
    return "World not found", 400
  character = elements.loadCharacter(get_db(), cid)
  if character == None:
    return "Character not found", 400

  return flask.render_template("view_character.html", world=world,
                               character=character)


@bp.route('/images/<id>', methods=["GET"])
def get_image(id):
  """
  Return an image
  """
  image = elements.getImage(get_db(), id)
  if image is None:
    return "Image not found", 400

  image_file = os.path.join(current_app.instance_path, image.filename)
  if not os.path.isfile(image_file):
    return "Image file not found", 400
  return flask.send_file(image_file, mimetype="image/webp")


@bp.route('/client/<wid>/<cid>', methods=["GET"])
def test_view_client(wid, cid):
  """
  Test Client view
  """
  world = elements.loadWorld(get_db(), wid)
  if world == None:
    return "World xxx not found", 400
  character = elements.loadCharacter(get_db(), cid)
  if character == None:
    return "Character xxx not found", 400

  return flask.render_template("test_client.html", world=world,
                               character=character)

@bp.route('/client/<session_id>', methods=["GET"])
def view_client(session_id):
  """
  Client view
  """
  return flask.render_template("client.html", session_id=session_id)


def generate_view(chat_session):
  current_view = chat_session.get_view();
  if current_view.get("logo") is not None:
    view = flask.url_for('worldai.view')
  elif (current_view.get("world") is not None and
      current_view.get("character") is not None):
    view = flask.url_for('worldai.view_character',
                         wid=current_view.get("world"),
                         cid=current_view.get("character"))
  elif current_view.get("world") is not None:
    view = flask.url_for('worldai.view_world',
                         id=current_view.get("world"))
  else:
    view = flask.url_for('worldai.list_worlds')
  return view


@bp.route('/chat/<session_id>', methods=["GET","POST"])
def chat_api(session_id):
  """
  Chat interface
  """
  path = os.path.join(current_app.instance_path, "chatfile")
  chat_session = chat.ChatSession.loadChatSession(path)
  
  if request.method == "GET":
    if current_app.config['TEST']:
      content = {
        "messages": [
          {
            "user": "some content",
            "assistant": "more content"
          },
          {
            "user": "test1",
            "assistant": "test2"
          },
          {
            "user": "Where is San Diego?",
            "assistant": "I am not sure who you are talking about?"
          },
          {
            "user": "Will people like my joke?",
            "assistant": "No. But they might chuckle to be polite."
          },
          {
            "user": "I think I should start a new online crypto currancy!",
            "assistant": "yeah, go for it"
          },
        ]
      }
    else:
      content = chat_session.chat_history()
      content["view"] = generate_view(chat_session)      

  else:
    if request.json.get("user") is None:
      content = { "error": "malformed input" }
    else:
      user_msg = request.json.get("user")
      
      if current_app.config['TEST']:
        content = {
          "assistant": "Sure Dave, whatever you say",
          "functions": [ "OpenDoor" ]
        }
      else:
        message = chat_session.chat_exchange(get_db(), user_msg)
        view = generate_view(chat_session)
        content = {
          "assistant": elements.textToHTML(message['content']),
          "view": view,
          "changes": chat_session.madeModifications()
        }
  chat_session.saveChatSession()
  return flask.jsonify(content)


@bp.route('/worlds/<wid>/characters/<cid>', methods=["GET", "POST"])
def get_character(wid, cid):
  """
  Get a character in JSON form
  """
  world = elements.loadWorld(get_db(), wid)
  if world == None:
    return { "error": "World not found"}, 400
  character = elements.loadCharacter(get_db(), cid)
  if character == None:
    return { "error": "Character not found"}, 400

  if request.method == "GET":  
    content = {
      "name": character.getName(),
      "description": character.getDescription(),
      "details": character.getDetails()
    }
  else:
    values = request.json
    content = {
      "name": values,
      "description": values,
      "details": values
    }
  return flask.jsonify(content)
  

