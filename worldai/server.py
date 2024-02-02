import os
import random
import json
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
from . import design_functions
from . import design_chat
from . import character_chat
from . import world_state
from . import chat_cli
from . import client_commands


def create_app(instance_path=None, test_config=None):
  if instance_path is None:
    app = Flask(__name__, instance_relative_config=True)
  else:
    app = Flask(__name__, instance_relative_config=True,
                instance_path=instance_path)
  app.config.from_mapping(
    SECRET_KEY='DEV',
    AUTH_KEY='auth',    
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY'),    
    DATABASE=os.path.join(app.instance_path, 'worldai.sqlite'),
    TESTING=False,
  )
  if test_config is None:
    app.config.from_prefixed_env()
    app.config.from_pyfile('config.py', silent=True)
  else:
    app.config.from_mapping(test_config)

  if app.config["TESTING"]:
    print("Test mode...")
    chat.TESTING = True
    design_functions.TESTING = True    

  # Configure logging
  BASE_DIR = os.getcwd()
  log_file_name = os.path.join(BASE_DIR, 'log-serve.log')
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
  design_functions.IMAGE_DIRECTORY = app.instance_path
  chat.MESSAGE_DIRECTORY = app.instance_path
  
  app.register_blueprint(bp)
  app.teardown_appcontext(close_db)  

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

@bp.cli.command('chat')
def run_chat_loop():
  """Text version of chat."""
  chat_cli.chat_loop()

@bp.cli.command('create-image-thumb')
@click.argument('id')
def create_image_thumb(id):
  """Create a thumbnail for an image."""
  image = elements.getImage(get_db(), id)
  if image is not None:
    design_functions.create_image_thumbnail(image)
    click.echo('Created thumbnail [%s] %s.' % (image.id, image.getThumbName()))
  else:
    click.echo(f'Error, no such image id:{id}')

@bp.cli.command('create-thumbs')
def create_image_thumbs():
  """Create a thumbnail for all images."""
  images = elements.getImages(get_db())
  for image in images:
    design_functions.create_image_thumbnail(image)
    click.echo('Created thumbnail [%s] %s.' % (image.id, image.getThumbName()))


@bp.cli.command('delete-image')
@click.argument('id')
def delete_image(id):
  """Delete an image."""
  image = elements.getImage(get_db(), id)
  if image is not None:
    elements.deleteImage(get_db(), current_app.instance_path, id)
    click.echo('Deleted image [%s].' % image.id)
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

@bp.cli.command('delete-world')
@click.argument('id')
def delete_world(id):
  """Delete a world and associated characters and images."""
  world = elements.loadWorld(get_db(), id)
  if world is not None:
    elements.deleteWorld(get_db(), current_app.instance_path, id)
    click.echo('Deleted world [%s] %s.' % (world.id,
                                           world.getName()))
  else:
    click.echo(f'Error, no such world id:{id}')



def list_images(parent_id):
  print("Listing images...")
  image_list = elements.listImages(get_db(), parent_id)
  for entry in image_list:
    print("Image(%s) filename:%s, prompt: %s" %
          (entry["id"], entry["filename"], entry["prompt"]))
    

@bp.cli.command('clear-state')
def clear_state():
  """Clear the game state due to a new format"""
  print("clearing state...")
  db = get_db()
  db.execute("DELETE FROM character_threads")  
  db.execute("DELETE FROM threads")
  db.execute("DELETE FROM world_state")
  db.commit()

  
@bp.cli.command('dump-worlds')
def dump_worlds():
  """Dump the contents of the world DB."""
  print("Loading worlds...")
  worlds = elements.listWorlds(get_db())
  print("%d worlds listed" % len(worlds))

  for (entry) in worlds:
    id = entry.getID()
    name = entry.getName()
    print(f"World({id}): {name}")
  
    world = elements.loadWorld(get_db(), id)
    print(world.getAllProperties())
    list_images(world.id)

    print("Loading characters...")
    characters = elements.listCharacters(get_db(), world.id)
    for (char_entry) in characters:
      id = char_entry.getID()
      name = char_entry.getName()
      print(f"Character({id}): {name}")

      character = elements.loadCharacter(get_db(), id)
      print(character.getAllProperties())
      list_images(character.id)

    print("Loading sites...")
    sites = elements.listSites(get_db(), world.id)
    for (site_entry) in sites:
      id = site_entry.getID()
      name = site_entry.getName()
      print(f"Site({id}): {name}")

      site = elements.loadSite(get_db(), id)
      print(site.getAllProperties())
      list_images(site.id)

    print("Loading items...")
    items = elements.listItems(get_db(), world.id)
    for (item_entry) in items:
      id = item_entry.getID()
      name = item_entry.getName()
      print(f"Item({id}): {name}")

      item = elements.loadItem(get_db(), id)
      print(item.getAllProperties())
      list_images(item.id)
      
  print("\n\n")

def extract_auth_key(headers):
  auth = request.headers.get('Authorization')
  if auth is not None:
    index = auth.find(' ')
    if index > 0:
      return auth[index+1:]
  return None
  
def auth_required(view):
  """
  Ensure authorization is valid on a json endpoint.
  """
  @functools.wraps(view)
  def wrapped_view(**kwargs):
    # Verify auth matches
    auth = extract_auth_key(request.headers)
    if auth != current_app.config['AUTH_KEY']:
      logging.info("auth failed: %s", auth)
      return { "error": "Invalid authorization header" }, 401
    return view(**kwargs)
  return wrapped_view

def login_required(view):
  """
  Ensure user is authenticated
  """
  @functools.wraps(view)
  def wrapped_view(**kwargs):
    auth = session.get('auth_key')
    if auth != current_app.config['AUTH_KEY']:
      flask.flash("Please enter an authorization key")
      return flask.redirect(flask.url_for('worldai.login'))
    return view(**kwargs)
  return wrapped_view

@bp.route('/login', methods=["GET", "POST"])
def login():
  """
  Login view
  """
  if request.method == "POST":
    auth = request.form["auth_key"]
    if auth != current_app.config['AUTH_KEY']:
      flask.flash("Authorization key does not match")
      return flask.redirect(flask.url_for('worldai.login'))
    session.permanent = True    
    session['auth_key'] = auth
    return flask.redirect(flask.url_for('worldai.top_view'))

  return flask.render_template("login.html")
  
  
@bp.route('/', methods=["GET"])
@login_required
def top_view():
  """
  Top level logo screen
  """
  return flask.render_template("top.html")

@bp.route('/ui/play', methods=["GET"])
@login_required
def play_page():
  """
  Serve the play.html file for the root of the UI
  """
  html_file = os.path.join(current_app.root_path,
                           'static/ui/play.html')
  with open(html_file) as f:
    html = f.read()
  
  return flask.render_template_string(
    html,
    auth_key=current_app.config['AUTH_KEY'])


@bp.route('/ui/design', methods=["GET"])
@login_required
def design_page():
  """
  Serve the design.html file for the root of the UI
  """
  html_file = os.path.join(current_app.root_path,
                           'static/ui/design.html')
  with open(html_file) as f:
    html = f.read()
  
  return flask.render_template_string(
    html,
    auth_key=current_app.config['AUTH_KEY'])


@bp.route('/ui/<path:path>', methods=["GET"])
def react_ui(path):
  """
  Serve react based files for the UI.
  """
  return flask.send_from_directory("static/ui", path)


@bp.route('/view/worlds', methods=["GET"])
@login_required
def list_worlds():
  """
  List Worlds
  """
  world_list = []
  worlds = elements.listWorlds(get_db())
  for (entry) in worlds:
    id = entry.getID()
    world = elements.loadWorld(get_db(), id)
    world_list.append((id, world.getName(), world.getDescription()))

  return flask.render_template("list_worlds.html", world_list=world_list)


@bp.route('/view/worlds/<id>', methods=["GET"])
@login_required
def view_world(id):
  """
  View a world
  """
  world = elements.loadWorld(get_db(), id)
  if world == None:
    return "World not found", 400

  worlds = elements.listWorlds(get_db())
  (pworld, nworld) = elements.getAdjacentElements(world.getIdName(),
                                                  worlds)  

  characters = elements.listCharacters(get_db(), world.id)
  char_list = []
  for entry in characters:
    char_id = entry.getID()
    char_name = entry.getName()
    character = elements.loadCharacter(get_db(), char_id)    
    char_list.append((char_id, char_name, character.getDescription()))

  items = elements.listItems(get_db(), world.id)
  item_list = []
  for entry in items:
    item_id = entry.getID()
    item_name = entry.getName()
    item = elements.loadItem(get_db(), item_id)    
    item_list.append((item_id, item_name, item.getDescription()))

  sites = elements.listSites(get_db(), world.id)
  site_list = []
  for entry in sites:
    site_id = entry.getID()
    site_name = entry.getName()
    site = elements.loadSite(get_db(), site_id)    
    site_list.append((site_id, site_name, site.getDescription()))
    
  return flask.render_template("view_world.html", world=world,
                               character_list=char_list,
                               item_list=item_list,
                               site_list=site_list,
                               pworld=pworld,
                               nworld=nworld)

@bp.route('/view/worlds/<wid>/characters/<id>', methods=["GET"])
@login_required
def view_character(wid, id):
  """
  View a character
  """
  world = elements.loadWorld(get_db(), wid)
  if world == None:
    return "World not found", 400
  character = elements.loadCharacter(get_db(), id)
  if character == None:
    return "Character not found", 400
  characters = elements.listCharacters(get_db(), wid)
  (pchar, nchar) = elements.getAdjacentElements(character.getIdName(),
                                                characters)  

  return flask.render_template("view_character.html", world=world,
                               character=character, pchar=pchar, nchar=nchar)

@bp.route('/view/worlds/<wid>/items/<id>', methods=["GET"])
@login_required
def view_item(wid, id):
  """
  View a character
  """
  world = elements.loadWorld(get_db(), wid)
  if world == None:
    return "World not found", 400
  item = elements.loadItem(get_db(), id)
  if item == None:
    return "Item not found", 400
  items = elements.listItems(get_db(), wid)
  (pitem, nitem) = elements.getAdjacentElements(item.getIdName(),
                                                items)  

  return flask.render_template("view_item.html", world=world,
                               item=item, nitem=nitem, pitem=pitem)

@bp.route('/view/worlds/<wid>/sites/<id>', methods=["GET"])
@login_required
def view_site(wid, id):
  """
  View a site
  """
  world = elements.loadWorld(get_db(), wid)
  if world == None:
    return "World not found", 400
  site = elements.loadSite(get_db(), id)
  if site == None:
    return "Site not found", 400
  sites = elements.listSites(get_db(), wid)
  (psite, nsite) = elements.getAdjacentElements(site.getIdName(),
                                             sites)  

  return flask.render_template("view_site.html", world=world,
                               site=site, psite=psite, nsite=nsite)


@bp.route('/images/<id>', methods=["GET"])
@login_required
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

@bp.route('/images/<id>/thumb', methods=["GET"])
@login_required
def get_image_thumb(id):
  """
  Return an image
  """
  image = elements.getImage(get_db(), id)
  if image is None:
    return "Image not found", 400

  image_file = os.path.join(current_app.instance_path, image.getThumbName())
  if not os.path.isfile(image_file):
    return "Image file not found", 400
  return flask.send_file(image_file, mimetype="image/webp")

def get_session_id():
  """
  Return an ID for the current session.
  Create one if needed.
  """
  session_id = session.get('session_id')
  if session_id is None:
    session_id = os.urandom(12).hex()
    session.permanent = True        
    session['session_id'] = session_id
  return session_id


@bp.route('/api/design_chat', methods=["GET","POST"])
@auth_required
def design_chat_api():
  """
  Chat interface
  """
  session_id = get_session_id()  
  chat_session = design_chat.DesignChatSession.loadChatSession(get_db(),
                                                               session_id)
  deleteSession = False
  
  if request.method == "GET":
      history = chat_session.chat_history()
      content = { "messages": history }  
      content['enabled'] =  True
      view = chat_session.get_view()        
      content['view'] = view
  else:
    command = request.json.get("command")
    if command == "start":
      user_msg = request.json.get("user")
      reply = chat_session.chat_start(get_db(), user_msg)
      content = reply.model_dump()

      # Add additional entries to the message
      content["changes"] = chat_session.madeChanges()
      content["enabled"] = True
      view = chat_session.get_view()        
      content['view'] = view

    elif command == "continue":
      msg_id = request.json.get("id")
      reply = chat_session.chat_continue(get_db(), msg_id)
      content = reply.model_dump()
      logging.info("design chat updates: %s", content["updates"])

      # Add additional entries to the message
      content["changes"] = chat_session.madeChanges()
      content["enabled"] = True
      view = chat_session.get_view()        
      content['view'] = view

    elif request.json.get("command") == "clear":
      content= { "status": "ok" }
      deleteSession = True
    else:
      content = { "error": "malformed input" }

  if not deleteSession:
    chat_session.saveChatSession(get_db())
  else:
    chat_session.deleteChatSession(get_db())    
  return flask.jsonify(content)

@bp.route('/api/design_chat/view', methods=["GET","POST"])
@auth_required
def design_chat_view_api():
  """
  Get / set current view for design chat.
  """
  session_id = get_session_id()
  chat_session = design_chat.DesignChatSession.loadChatSession(get_db(),
                                                               session_id)
  if request.method == "GET":
    content = { 'view' : chat_session.get_view() }
  else:
    if request.json.get("view") is not None:
      view = request.json["view"]
      logging.info(f"view: {view}")
      chat_session.set_view(get_db(), view)
      logging.info("view2: %s", chat_session.get_view())
      content = { 'view' : chat_session.get_view() }      
    else:
      content = { "error": "malformed input" }
  chat_session.saveChatSession(get_db())
  return flask.jsonify(content)


@bp.route('/api/initdata', methods=["GET"])
@auth_required
def get_init_data():
  """
  Initial load of information for clients
  """
  # Returns session id and world id last loaded
  session_id = get_session_id()
  world_id = session.get('world_id', "")

  return { "session_id": session_id,
           "world_id": world_id }



@bp.route('/api/worlds', methods=["GET"])
@auth_required
def worlds_list():
  """
  API to access worldlist
  """
  # Reset last opened world
  if session.get('world_id'):
    del session['world_id']  
  world_list = []
  worlds = elements.listWorlds(get_db())
  for (entry) in worlds:
    wid = entry.getID()
    world = elements.loadWorld(get_db(), wid)
    image_prop = getElementThumbProperty(world)
    world_list.append({"id": wid,
                       "name": world.getName(),
                       "description": world.getDescription(),
                       "image": image_prop })

  return flask.jsonify(world_list)


@bp.route('/api/worlds/<wid>', methods=["GET"])
@auth_required
def worlds(wid):
  """
  API to access a world
  """
  world = elements.loadWorld(get_db(), wid)
  if world == None:
    return { "error", "World not found"}, 400

  # Save last opened in session
  session['world_id'] = wid
  images = getElementImageProps(world)
  result = world.getAllProperties()
  result["images"] = images
  
  return result

def getElementThumbProperty(element):
  """
  Return a property referencing an image for an element
  """
  # May be None
  image_id = element.getImageByIndex(0)
  if image_id is None:
    url = flask.url_for('static',
                        filename="question-square-fill.svg")
    image_prop = { "id": "0", "url": url }
  else:
    image_prop = { "id": image_id,
                   "url": flask.url_for('worldai.get_image_thumb',
                                        id=image_id) }
  return image_prop

def getElementImageProps(element):
  images = []
  for image in element.getImages():
    url = flask.url_for('worldai.get_image', id=image)
    images.append({ "id": image, "url": url})

  if len(images) == 0:
    url = flask.url_for('static',
                        filename="question-square-fill.svg")
    images.append({ "id": "0", "url": url})
  return images




@bp.route('/api/worlds/<wid>/characters', methods=["GET"])
@auth_required
def characters_list(wid):
  """
  API to get the list of characters for a world
  """
  # Save last opened in session
  session['world_id'] = wid
  
  character_list = []
  session_id = get_session_id()
  world = elements.loadWorld(get_db(), wid)  
  if world is None:
    return { "error", "World not found"}, 400
  wstate_id = world_state.getWorldStateID(get_db(), session_id, wid)
  wstate = world_state.loadWorldState(get_db(), wstate_id)  
  characters = elements.listCharacters(get_db(), wid)
  
  for entry in characters:
    id = entry.getID()
    character = elements.loadCharacter(get_db(), id)
    image_prop = getElementThumbProperty(character)
      
    character_list.append(
      {"id": id,
       "name": character.getName(),
       "description": character.getDescription(),
       "givenSupport": wstate.getFriendship(id) > 0,
       "image": image_prop })

  return flask.jsonify(character_list)


@bp.route('/api/worlds/<wid>/characters/<id>', methods=["GET"])
@auth_required
def characters(wid, id):
  """
  API to access a character
  """
  session_id = get_session_id()
  wstate_id = world_state.getWorldStateID(get_db(), session_id, wid)
  wstate = world_state.loadWorldState(get_db(), wstate_id)  
  character = elements.loadCharacter(get_db(), id)
  if character == None or character.parent_id != wid:
    return { "error", "Character not found"}, 400

  images = getElementImageProps(character)
  result = character.getAllProperties()
  result["images"] = images

  return result

@bp.route('/api/worlds/<wid>/sites', methods=["GET"])
@auth_required
def site_list(wid):
  """
  Get a list of sites
  """
  # Save last opened in session
  session['world_id'] = wid
  world = elements.loadWorld(get_db(), wid)
  if world is None:
    return { "error", "World not found"}, 400

  site_list = []
  session_id = get_session_id()
  wstate_id = world_state.getWorldStateID(get_db(), session_id, wid)
  wstate = world_state.loadWorldState(get_db(), wstate_id)  
  sites = elements.listSites(get_db(), wid)

  for entry in sites:
    id = entry.getID()
    site = elements.loadSite(get_db(), id)
    image_prop = getElementThumbProperty(site)
      
    site_list.append(
      {"id": id,
       "name": site.getName(),
       "description": site.getDescription(),
       "present": wstate.getLocation() == id,
       "locked": wstate.isSiteLocked(id),
       "image": image_prop })
  return site_list

@bp.route('/api/worlds/<wid>/sites/<sid>', methods=["GET"])
@auth_required
def site(wid, sid):
  """
  API to load info and state for a site
  """
  session_id = get_session_id()
  world = elements.loadWorld(get_db(), wid)  
  if world is None:
    return { "error", "World not found"}, 400
  wstate_id = world_state.getWorldStateID(get_db(), session_id, wid)
  wstate = world_state.loadWorldState(get_db(), wstate_id)
  site = elements.loadSite(get_db(), sid)
  if site == None:
    return { "error", "Site not found"}, 400

  chat_char_id = wstate.getChatCharacter()
  images = getElementImageProps(site)
  result = site.getAllProperties()
  result["images"] = images

  characters = []
  cid_list = wstate.getCharactersAtLocation(sid)
  for cid in cid_list:
    character = elements.loadCharacter(get_db(), cid)
    # TODO: make more DRY
    image_prop = getElementThumbProperty(character)
    record = {"id": cid,
              "name": character.getName(),
              "description": character.getDescription(),
              "givenSupport": wstate.getFriendship(cid) > 0,
              "image": image_prop }
    characters.append(record)

  result["characters"] = characters    
  result["chatting"] = chat_char_id
  result["current_time"] = wstate.getCurrentTime()
      
  items = []
  iid_list = wstate.getItemsAtLocation(sid)
  for iid in iid_list:
    item = elements.loadItem(get_db(), iid)
    # TODO: make more DRY
    image_prop = getElementThumbProperty(item)
    items.append(
      {"id": iid,
       "name": item.getName(),
       "description": item.getDescription(),
       "mobile": item.getIsMobile(),
       "image": image_prop })
  result["items"] = items

  return result

@bp.route('/api/worlds/<wid>/items', methods=["GET"])
@auth_required
def items_list(wid):
  """
  API to get the items for a world
  """
  # Save last opened in session
  session['world_id'] = wid
  
  item_list = []
  session_id = get_session_id()
  world = elements.loadWorld(get_db(), wid)  
  if world is None:
    return { "error", "World not found"}, 400
  wstate_id = world_state.getWorldStateID(get_db(), session_id, wid)
  wstate = world_state.loadWorldState(get_db(), wstate_id)  
  items = elements.listItems(get_db(), wid)
  
  for entry in items:
    id = entry.getID()
    item = elements.loadItem(get_db(), id)
    image_prop = getElementThumbProperty(item)
      
    item_list.append(
      {"id": id,
       "name": item.getName(),
       "description": item.getDescription(),
       "have_item":  wstate.hasItem(id),
       "image": image_prop })

  return item_list


@bp.route('/api/worlds/<wid>/items/<id>', methods=["GET"])
@auth_required
def items(wid, id):
  """
  API to access an item
  """
  session_id = get_session_id()
  item = elements.loadItem(get_db(), id)
  if item == None or item.parent_id != wid:
    return { "error", "Item not found"}, 400

  images = getElementImageProps(item)
  result = item.getAllProperties()
  result["images"] = images
  image_prop = getElementThumbProperty(item)  
  result["image"] = image_prop
  
  return result



@bp.route('/api/worlds/<wid>/command', methods=["POST"])
@auth_required
def command(wid):
  """
  API to make player changes
  """
  session_id = get_session_id()
  world = elements.loadWorld(get_db(), wid)  
  if world is None:
    return { "error", "World not found"}, 400
  wstate_id = world_state.getWorldStateID(get_db(), session_id, wid)
  wstate = world_state.loadWorldState(get_db(), wstate_id)

  command = client_commands.Command(**request.json)
  logging.info("commmand name %s", command.name)
  logging.info("location: %s", wstate.getLocation())
  client_actions = client_commands.ClientActions(get_db(), world, wstate)
  response = client_actions.ExecCommand(command)

  if response.changed:
    logging.info("COMMAND: save world state")
    world_state.saveWorldState(get_db(), wstate)

  return response.model_dump()
          

@bp.route('/api/worlds/<wid>/player', methods=["GET"])
@auth_required
def player(wid):
  """
  API to get player status
  """
  session_id = get_session_id()
  world = elements.loadWorld(get_db(), wid)  
  if world is None:
    return { "error", "World not found"}, 400
  wstate_id = world_state.getWorldStateID(get_db(), session_id, wid)
  wstate = world_state.loadWorldState(get_db(), wstate_id)

  player_data = client_commands.LoadPlayerData(get_db(), world, wstate)
  response = player_data.model_dump()
  response["current_time"] = wstate.getCurrentTime()  
  return response

@bp.route('/api/worlds/<wid>/characters/<id>/instance', methods=["GET"])
@auth_required
def character_stats(wid, id):
  """
  API to get character status
  """
  session_id = get_session_id()
  world = elements.loadWorld(get_db(), wid)  
  if world is None:
    return { "error", "World not found"}, 400
  wstate_id = world_state.getWorldStateID(get_db(), session_id, wid)
  wstate = world_state.loadWorldState(get_db(), wstate_id)

  character_data = client_commands.LoadCharacterData(get_db(),
                                                     world, wstate, id)
  response = character_data.model_dump()
  response["current_time"] = wstate.getCurrentTime()  
  return response

@bp.route('/api/worlds/<wid>/characters/<id>/thread', methods=["GET","POST"])
@auth_required
def thread_api(wid, id):
  """
  Character chat interface
  """
  session_id = get_session_id()
  wstate_id = world_state.getWorldStateID(get_db(), session_id, wid)
  # TODO: this is where we need lock for updating  
  chat_session = character_chat.CharacterChat.loadChatSession(get_db(),
                                                              wstate_id,
                                                              wid,
                                                              id)
  if request.method == "GET":
    history = chat_session.chat_history()    
    content = { "messages": history }
  elif request.json.get("user") is not None:
      user_msg = request.json.get("user")
      result = chat_session.chat_message(get_db(), user_msg)
      content = result.model_dump()
  else:
    content = { "error": "malformed input" }

  # Player and character must be in same location to continue to chat.
  logging.info("threads API: load world state")
  wstate = world_state.loadWorldState(get_db(), wstate_id)  
  enabled = (wstate.getCharacterLocation(id) == wstate.getLocation())
  logging.info("location: %s", wstate.getLocation())
  logging.info("char location: %s", wstate.getCharacterLocation(id)) 
  engaged = (wstate.getChatCharacter() == id)
  logging.info("enabled: %s", enabled)
  logging.info("engaged: %s", engaged)  
  content["enabled"] = enabled and engaged

  chat_session.saveChatSession(get_db())
  return content


@bp.route('/api/worlds/<wid>/characters/<cid>/action', methods=["POST"])
@auth_required
def action_api(wid, cid):
  """
  Action with character

  Combination use artifact with a character chat.
  """
  session_id = get_session_id()
  world = elements.loadWorld(get_db(), wid)  
  if world is None:
    return { "error", "World not found"}, 400
  
  wstate_id = world_state.getWorldStateID(get_db(), session_id, wid)
  wstate = world_state.loadWorldState(get_db(), wstate_id)  
  item_id = request.json.get("item")

  # Run the use command
  client_actions = client_commands.ClientActions(get_db(), world, wstate)
  print("use item %s on character %s" % (item_id, cid))
  (changed, message, event) = client_actions.UseItemCharacter(item_id, cid)
  print("result - changed: %s, message: %s, event: %s" % (changed,
                                                          message,
                                                          event))
  character = client_commands.LoadCharacterData(get_db(),
                                                world, wstate, cid)
  if changed:
    # Save state since chat functions may load it again
    world_state.saveWorldState(get_db(), wstate)

  if len(event) > 0:
    chat_session = character_chat.CharacterChat.loadChatSession(get_db(),
                                                                wstate_id,
                                                                wid,
                                                                cid)
    # Run event
    result = chat_session.chat_event(get_db(), event)
    chat_session.saveChatSession(get_db())
  else:
    result = chat.ChatResponse(id=os.urandom(8).hex(),
                               done=True)

  content = result.model_dump()
  content["message"] = message
  content["changed"] = changed

  # Player and character must be in same location to continue chat.
  wstate = world_state.loadWorldState(get_db(), wstate_id)  
  enabled = (wstate.getCharacterLocation(cid) == wstate.getLocation())
  engaged = (wstate.getChatCharacter() == cid)
  content["enabled"] = enabled and engaged

  return content

