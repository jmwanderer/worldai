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
    chat_functions.TESTING = True    

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
    print(world.getPropertiesJSON())
    list_images(world.id)

    print("Loading characters...")
    characters = elements.listCharacters(get_db(), world.id)
    for (char_entry) in characters:
      id = char_entry.getID()
      name = char_entry.getName()
      print(f"Character({id}): {name}")

      character = elements.loadCharacter(get_db(), id)
      print(character.getPropertiesJSON())
      list_images(character.id)
    
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

@bp.route('/react/<path:path>', methods=["GET"])
def react(path):
  """
  """
  return flask.send_from_directory("static/react", path)

@bp.route('/react', methods=["GET"])
def react_base():
  """
  """
  return flask.render_template("index.html")


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


@bp.route('/client', methods=["GET"])
@login_required
def view_client():
  """
  Client view
  """
  session_id = session.get('session_id')
  if session_id is None:
    session_id = os.urandom(12).hex()
    session['session_id'] = session_id


  return flask.render_template("client.html",
                               session_id=session_id,
                               auth_key=current_app.config['AUTH_KEY'])


@bp.route('/chat/<session_id>', methods=["GET","POST"])
@auth_required
def chat_api(session_id):
  """
  Chat interface
  """
  chat_session = chat.ChatSession.loadChatSession(get_db(), session_id)
  deleteSession = False
  
  if request.method == "GET":
      content = chat_session.chat_history()
      content['view'] = chat_session.get_view()
  else:
    if request.json.get("user") is not None:
      user_msg = request.json.get("user")
      view = request.json.get("view")
      chat_session.set_view(view)
      message = chat_session.chat_message(get_db(), user_msg)
      content = {
        "assistant": chat_functions.parseResponseText(message['content']),
        "changes": chat_session.madeModifications()
      }
      content['view'] = chat_session.get_view()
    elif request.json.get("command") is not None:
      content= { "status": "ok" }
      deleteSession = True
    else:
      content = { "error": "malformed input" }

  if not deleteSession:
    chat_session.saveChatSession(get_db())
  else:
    chat_session.deleteChatSession(get_db())    
  return flask.jsonify(content)


@bp.route('/view_props', methods=["POST"])
@auth_required
def view_props():
  """
  Return view properties for an element.
  - HTML to display
  - List of image urls
  """
  wid = request.json.get("wid")
  element_type = request.json.get("element_type")
  id = request.json.get("id")
  
  images = []

  if wid is None:
    # List of worlds view
    world_list = []
    worlds = elements.listWorlds(get_db())
    for (entry) in worlds:
      id = entry.getID()
      world = elements.loadWorld(get_db(), id)
      world_list.append((world.getElemTag(),
                         world.getName(),
                         world.getDescription()))
    html = flask.render_template("view.html", obj="worlds",
                                 world_list=world_list)

  elif element_type == elements.ElementType.CharacterType():
    # Character view
    world = elements.loadWorld(get_db(), wid)
    if world == None:
      return "World not found", 400
    character = elements.loadCharacter(get_db(), id)
    if character == None:
      return "Character not found", 400

    # Setup next / prev
    characters = elements.listCharacters(get_db(), world.id)
    (pc, nc) = elements.getAdjacentElements(character.getIdName(),
                                            characters)
    # Change to elemTag
    pc = elements.idNameToElemTag(get_db(), pc)
    nc = elements.idNameToElemTag(get_db(), nc)    

    for image in character.getImages():
      url = flask.url_for('worldai.get_image', id=image)
      images.append(url)

    html = flask.render_template("view.html", obj="character",
                                 world=world,
                                 next=nc, prev=pc,
                                 character=character)

  elif element_type == elements.ElementType.ItemType():
    # Item view
    world = elements.loadWorld(get_db(), wid)
    if world == None:
      return "World not found", 400
    item = elements.loadItem(get_db(), id)
    if item == None:
      return "Item not found", 400

    # Setup next / prev
    items = elements.listItems(get_db(), world.id)
    (pi, ni) = elements.getAdjacentElements(item.getIdName(),
                                            items)
    # Change to elemTag
    pi = elements.idNameToElemTag(get_db(), pi)
    ni = elements.idNameToElemTag(get_db(), ni)    
    
    for image in item.getImages():
      url = flask.url_for('worldai.get_image', id=image)
      images.append(url)

    html = flask.render_template("view.html", obj="item",
                                 world=world,
                                 next=ni, prev=pi,
                                 item=item)

  elif element_type == elements.ElementType.SiteType():
    # Site view
    world = elements.loadWorld(get_db(), wid)
    if world == None:
      return "World not found", 400
    site = elements.loadSite(get_db(), id)
    if site == None:
      return "Site not found", 400

    # Setup next / prev
    sites = elements.listSites(get_db(), world.id)
    (ps, ns) = elements.getAdjacentElements(site.getIdName(),
                                            sites)
    # Change to elemTag
    ps = elements.idNameToElemTag(get_db(), ps)
    ns = elements.idNameToElemTag(get_db(), ns)    
    
    for image in site.getImages():
      url = flask.url_for('worldai.get_image', id=image)
      images.append(url)
   
    html = flask.render_template("view.html", obj="site", world=world,
                                 next=ns, prev=ps,
                                 site=site)

  elif element_type == elements.ElementType.WorldType():
    # World view
    world = elements.loadWorld(get_db(), wid)
    if world == None:
      return "World not found", 400

    characters = elements.listCharacters(get_db(), world.id)
    char_list = []
    for entry in characters:
      char_id = entry.getID()
      char_name = entry.getName()
      character = elements.loadCharacter(get_db(), char_id)    
      char_list.append((character.getElemTag(), char_name,
                        character.getDescription()))

    items = elements.listItems(get_db(), world.id)
    item_list = []
    for entry in items:
      item_id = entry.getID()
      item_name = entry.getName()
      item = elements.loadItem(get_db(), item_id)    
      item_list.append((item.getElemTag(), item_name, item.getDescription()))

    sites = elements.listSites(get_db(), world.id)
    site_list = []
    for entry in sites:
      site_id = entry.getID()
      site_name = entry.getName()
      site = elements.loadSite(get_db(), site_id)    
      site_list.append((site.getElemTag(), site_name, site.getDescription()))
      
    for image in world.getImages():
      url = flask.url_for('worldai.get_image', id=image)
      images.append(url)
    
    html = flask.render_template("view.html", obj='world', world=world,
                                 character_list=char_list,
                                 item_list=item_list,
                                 site_list=site_list)
  else:
    return { "error": "malformed input" }        

  return flask.jsonify({ "html": html, "images": images })
  


@bp.route('/threads/<id>', methods=["GET","POST"])
@auth_required
def threads(id):
  """
  Chat interface
  """
  if request.method == "GET":
    content = { "messages": [
      { "id": "1001",      
        "user": "Hi There",
        "reply": "This is a reply message" },
      { "id": "1002",      
        "user": "How about this is a user message",
        "reply": "This is still a reply message" },
      { "id": "1003",      
        "user": "Can you say anything else?",
        "reply": "No, not really." },
      { "id": "1004",      
        "user": "Why not?",
        "reply": "Just the way it is" },
      ]}
  elif request.json.get("user") is not None:
      user_msg = request.json.get("user")
      content = {
        "id": os.urandom(4).hex(),
        "user": user_msg,
        "reply": "Hey, how is it going?"
      }
      time.sleep(2)
  else:
    content = { "error": "malformed input" }

  return content
