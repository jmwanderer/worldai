import os
import os.path
import pathlib
import time
import functools
import sqlite3
import io
import flask
from flask import Flask
from flask import request
from flask import Blueprint, g, current_app, session
from werkzeug.middleware.proxy_fix import ProxyFix
import werkzeug.utils
import logging
import click

from . import elements


def create_app(instance_path=None):
  if instance_path is None:
    app = Flask(__name__, instance_relative_config=True)
  else:
    app = Flask(__name__, instance_relative_config=True,
                instance_path=instance_path)
  app.config.from_mapping(
    SECRET_KEY='DEV',
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

  app.register_blueprint(bp)

  @app.errorhandler(Exception)
  def handle_exception(e):
    logging.exception("Internal error")
    return e
  return app


def get_db():
  if 'db' not in g:
    g.db = sqlite3.connect(
      current_app.config['DATABASE'],
      detect_types=sqlite3.PARSE_DECLTYPES)
    g.db.row_factory = sqlite3.Row
  return g.db

def close_db(e=None):
  db = g.pop('db', None)
  if db is not None:
    db.close()


bp = Blueprint('worldai', __name__, cli_group=None)

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



