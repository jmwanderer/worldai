import functools
import logging
import os
import os.path
import sys
import threading
import time

import click
import flask
import openai
from flask import Blueprint, Flask, current_app, g, request, session
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.wrappers import Response as Response

from . import (character_chat, chat, chat_cli, client, client_commands,
               db_access, design_chat, design_functions, element_info,
               elements, info_set, users, world_state)


def create_app(instance_path=None, test_config=None):
    if instance_path is None:
        app = Flask(__name__, instance_relative_config=True)
    else:
        app = Flask(
            __name__, instance_relative_config=True, instance_path=instance_path
        )
    app.config.from_mapping(
        SECRET_KEY="DEV",
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
        DATABASE=os.path.join(app.instance_path, "worldai.sqlite"),
        TESTING=False,
    )
    if test_config is None:
        app.config.from_prefixed_env()
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    if app.config["TESTING"]:
        print("Test mode...")
        chat.TESTING = True
        design_functions.TESTING = True

    # Configure logging
    BASE_DIR = os.getcwd()
    log_file_name = os.path.join(BASE_DIR, "log-serve.log")
    FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        filename=log_file_name,
        level=logging.INFO,
        format=FORMAT,
    )
    db_access.init_config(app.config["DATABASE"])
    openai.api_key = app.config["OPENAI_API_KEY"]

    logging.info("Starting worldai.server: %s", __name__)

    # If so configured, setup for running behind a reverse proxy.
    if app.config.get("PROXY_CONFIG"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
        logging.info("set proxy fix")

    try:
        logging.info("instance path = %s", app.instance_path)
        os.makedirs(app.instance_path)
    except OSError:
        pass
    design_functions.IMAGE_DIRECTORY = app.instance_path
    chat.MESSAGE_DIRECTORY = app.instance_path

    app.register_blueprint(bp)
    app.teardown_appcontext(close_db)

    bg_thread = threading.Thread(target=BgEmbedTask)
    bg_thread.daemon = True
    bg_thread.start()

    @app.errorhandler(Exception)
    def handle_exception(e):
        logging.exception("Internal error")
        return e

    return app


def BgEmbedTask():
    db = db_access.open_db()
    while True:
        time.sleep(30)
        count = 0
        while info_set.addEmbeddings(db) and count < 10:
            count = count + 1
        if count > 0:
            logging.info("Updated %d embeddings.", count)
    db.close()


def get_db():
    if "db" not in g:
        g.db = db_access.open_db()
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


bp = Blueprint("worldai", __name__, cli_group=None)


@bp.cli.command("add-user")
@click.argument("username")
def add_user(username: str):
    """ 
    Create a user entry and print the authkey
    """
    key = users.add_user(get_db(), username)
    click.echo("Added user %s. Auth key = %s" % (username, key))


@bp.cli.command("chat")
def run_chat_loop():
    """Text version of chat."""
    chat_cli.chat_loop()


@bp.cli.command("create-image-thumb")
@click.argument("id")
def create_image_thumb(arg: str):
    """Create a thumbnail for an image."""
    eid = elements.ElemID(arg)
    image = elements.getImage(get_db(), eid)
    if image is not None:
        design_functions.create_image_thumbnail(image)
        click.echo("Created thumbnail [%s] %s." % (image.getID(), image.getThumbName()))
    else:
        click.echo(f"Error, no such image id:{eid}")


@bp.cli.command("create-thumbs")
def create_image_thumbs() -> None:
    """Create a thumbnail for all images."""
    images = elements.getImages(get_db())
    for image in images:
        design_functions.create_image_thumbnail(image)
        click.echo("Created thumbnail [%s] %s." % (image.getID(), image.getThumbName()))


@bp.cli.command("delete-image")
@click.argument("id")
def delete_image(arg: str):
    """Delete an image."""
    eid = elements.ElemID(arg)
    image = elements.getImage(get_db(), eid)
    if image is not None:
        elements.deleteImage(get_db(), current_app.instance_path, eid)
        click.echo("Deleted image [%s]." % image.getID())
    else:
        click.echo(f"Error, no such image id:{eid}")


@bp.cli.command("delete-character")
@click.argument("id")
def delete_character(arg: str):
    """Delete a character and associated images."""
    eid = elements.ElemID(arg)
    character = elements.loadCharacter(get_db(), eid)
    if character is not None:
        element_info.DeleteElementInfo(get_db(), eid)
        elements.deleteCharacter(get_db(), current_app.instance_path, eid)
        click.echo(
            "Deleted character [%s] %s." % (character.getID(), character.getName())
        )
    else:
        click.echo(f"Error, no such character id:{eid}")


@bp.cli.command("delete-world")
@click.argument("id")
def delete_world(arg):
    """Delete a world and associated characters and images."""
    wid = elements.WorldID(arg)
    world = elements.loadWorld(get_db(), wid)
    if world is not None:
        elements.deleteWorld(get_db(), current_app.instance_path, wid)
        click.echo("Deleted world [%s] %s." % (world.getID(), world.getName()))
    else:
        click.echo(f"Error, no such world id:{wid}")


@bp.cli.command("list-worlds")
def list_worlds_cli():
    worlds = elements.listWorlds(get_db())
    print("%d worlds listed" % len(worlds))

    for entry in worlds:
        click.echo("[%s}: %s" % (entry.getID(), entry.getName()))


@bp.cli.command("write-elements")
def write_elements_cli() -> None:
    worlds = elements.listWorlds(get_db())
    for entry in worlds:
        click.echo(f"World: {entry.getName()}")
        world = elements.loadWorld(get_db(), entry.getID())
        if world is None:
            continue
        elements.updateWorld(get_db(), world)

        characters = elements.listCharacters(get_db(), world.getID())
        for centry in characters:
            click.echo(f"Character: {centry.getName()}")
            character = elements.loadCharacter(get_db(), centry.getID())
            if character is not None:
                elements.updateCharacter(get_db(), character)

        items = elements.listItems(get_db(), world.getID())
        for ientry in items:
            click.echo(f"Item: {ientry.getName()}")
            item = elements.loadItem(get_db(), ientry.getID())
            if item is not None:
                elements.updateItem(get_db(), item)

        sites = elements.listSites(get_db(), world.getID())
        for sentry in sites:
            click.echo(f"Site: {sentry.getName()}")
            site = elements.loadSite(get_db(), sentry.getID())
            if site is not None:
                elements.updateSite(get_db(), site)

        sites = elements.listDocuments(get_db(), world.getID())
        for dentry in sites:
            click.echo(f"Doc: {dentry.getName()}")
            doc = elements.loadDocument(get_db(), dentry.getID())
            if doc is not None:
                elements.updateDocument(get_db(), doc)


@bp.cli.command("update-embeddings")
@click.argument("world_name")
def update_embeddings(world_name: str) -> None:
    world = elements.findWorld(get_db(), world_name)
    if world is None:
        click.echo("No such world %s" % world_name)
        return
    update_world_embeddings(world)


def update_world_embeddings(world: elements.World) -> None:
    click.echo(f"Update world {world.getName()}")
    element_info.UpdateElementInfo(get_db(), world)

    characters = elements.listCharacters(get_db(), world.getID())
    sites = elements.listSites(get_db(), world.getID())
    items = elements.listItems(get_db(), world.getID())
    docs = elements.listDocuments(get_db(), world.getID())

    for cid in characters:
        character = elements.loadCharacter(get_db(), cid.getID())
        if character is None:
            continue
        click.echo(f"Update character {character.getName()}")
        element_info.UpdateElementInfo(get_db(), character)
    for iid in items:
        item = elements.loadItem(get_db(), iid.getID())
        if item is None:
            continue
        click.echo(f"Update item {item.getName()}")
        element_info.UpdateElementInfo(get_db(), item)
    for sid in sites:
        site = elements.loadSite(get_db(), sid.getID())
        if site is None:
            continue
        click.echo(f"Update site {site.getName()}")
        element_info.UpdateElementInfo(get_db(), site)
    for did in docs:
        doc = elements.loadSite(get_db(), did.getID())
        if doc is None:
            continue
        click.echo(f"Update site {doc.getName()}")
        element_info.UpdateElementInfo(get_db(), doc)
    click.echo("done")


@bp.cli.command("update-all-embeddings")
def update_all_embeddings() -> None:
    worlds = elements.listWorlds(get_db())
    for entry in worlds:
        world = elements.loadWorld(get_db(), entry.getID())
        if world is not None:
            update_world_embeddings(world)


def list_images(parent_id: elements.ElemID) -> None:
    print("Listing images...")
    image_list = elements.listImages(get_db(), parent_id)
    for entry in image_list:
        print(
            "Image(%s) filename:%s, prompt: %s"
            % (entry["id"], entry["filename"], entry["prompt"])
        )


@bp.cli.command("clear-all-world-state")
def clear_all_world_state() -> None:
    """Clear the game state due to a new format"""
    print("really clear everything????")
    answer = sys.stdin.readline().strip()
    if answer != "y" and answer != "Y":
        print("aborting")
        return

    print("clearing state...")
    db = get_db()
    sql = "DELETE FROM info_chunks WHERE doc_id IN (SELECT id FROM info_docs WHERE wstate_id IS NOT NULL)"
    db.execute(sql)
    sql = "DELETE FROM info_docs WHERE info_docs.wstate_id  is NOT NULL"
    db.execute(sql)
    db.execute("DELETE FROM character_threads")
    db.execute("DELETE FROM threads")
    db.execute("DELETE FROM world_state")
    db.commit()


@bp.cli.command("clear-world-state")
@click.argument("wstate_id")
def clear_world_state(wstate_id) -> None:
    """Clear a specific wstate"""
    print("clearing state for %s..." % wstate_id)
    world_state.clearWorldState(get_db(), wstate_id)

@bp.cli.command("dump-worlds")
def dump_worlds() -> None:
    """Dump the contents of the world DB."""
    print("Loading worlds...")
    worlds = elements.listWorlds(get_db())
    print("%d worlds listed" % len(worlds))

    for entry in worlds:
        eid = entry.getID()
        name = entry.getName()
        print(f"World({eid}): {name}")

        world = elements.loadWorld(get_db(), eid)
        if world is None:
            continue

        print(world.getAllProperties())
        list_images(world.getID())

        print("Loading characters...")
        characters = elements.listCharacters(get_db(), world.getID())
        for char_entry in characters:
            eid = char_entry.getID()
            name = char_entry.getName()
            print(f"Character({eid}): {name}")

            character = elements.loadCharacter(get_db(), eid)
            if character is None:
                continue
            print(character.getAllProperties())
            list_images(character.getID())

        print("Loading sites...")
        sites = elements.listSites(get_db(), world.getID())
        for site_entry in sites:
            sid = site_entry.getID()
            name = site_entry.getName()
            print(f"Site({sid}): {name}")

            site = elements.loadSite(get_db(), sid)
            if site is None:
                continue
            print(site.getAllProperties())
            list_images(site.getID())

        print("Loading items...")
        items = elements.listItems(get_db(), world.getID())
        for item_entry in items:
            iid = item_entry.getID()
            name = item_entry.getName()
            print(f"Item({iid}): {name}")

            item = elements.loadItem(get_db(), iid)
            if item is None:
                continue
            print(item.getAllProperties())
            list_images(item.getID())

    print("\n\n")


def extract_auth_key(headers: dict) -> str | None:
    auth = headers.get("Authorization")
    if auth is not None:
        index = auth.find(" ")
        if index > 0:
            return auth[index + 1 :]
    return None


def auth_required(view):
    """
    Ensure authorization is valid on a json endpoint.
    """

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        # Verify auth matches
        auth = extract_auth_key(request.headers)
        user_id = users.find_by_auth_key(get_db(), auth)
        if user_id is None:
            logging.info("auth failed: %s", auth)
            return {"error": "Invalid authorization header"}, 401
        g.user_id = user_id
        return view(**kwargs)

    return wrapped_view


def login_required(view):
    """
    Ensure user is authenticated
    """

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        auth = session.get("auth_key")
        user_id = users.find_by_auth_key(get_db(), auth)
        if user_id is None:
            flask.flash("Please enter an authorization key")
            return flask.redirect(flask.url_for("worldai.login"))
        g.user_id = user_id
        return view(**kwargs)

    return wrapped_view


@bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Login view
    """
    if request.method == "POST":
        auth = request.form["auth_key"]
        user_id = users.find_by_auth_key(get_db(), auth)
        if user_id is None:
            flask.flash("Authorization key does not match")
            return flask.redirect(flask.url_for("worldai.login"))
        session.permanent = True
        session["auth_key"] = auth
        return flask.redirect(flask.url_for("worldai.top_view"))

    return flask.render_template("login.html")


@bp.route("/", methods=["GET"])
@login_required
def top_view():
    """
    Top level logo screen
    """
    return flask.render_template("top.html")


@bp.route("/ui/play", methods=["GET"])
@login_required
def play_page():
    """
    Serve the play.html file for the root of the UI
    """
    html_file = os.path.join(current_app.root_path, "static/ui/play.html")
    with open(html_file) as f:
        html = f.read()

    auth_key = users.get_auth_key(get_db(), g.user_id)
    return flask.render_template_string(html, auth_key=auth_key)


@bp.route("/ui/design", methods=["GET"])
@login_required
def design_page():
    """
    Serve the design.html file for the root of the UI
    """
    html_file = os.path.join(current_app.root_path, "static/ui/design.html")
    with open(html_file) as f:
        html = f.read()

    auth_key = users.get_auth_key(get_db(), g.user_id)
    return flask.render_template_string(html, auth_key=auth_key)


@bp.route("/ui/<path:path>", methods=["GET"])
def react_ui(path):
    """
    Serve react based files for the UI.
    """
    return flask.send_from_directory("static/ui", path)


@bp.route("/view/worlds", methods=["GET"])
@login_required
def list_worlds():
    """
    List Worlds
    """
    world_list = []
    worlds = elements.listWorlds(get_db())
    for entry in worlds:
        wid = entry.getID()
        world = elements.loadWorld(get_db(), wid)
        if world is not None:
            world_list.append((wid, world.getName(), world.getDescription()))

    return flask.render_template("list_worlds.html", world_list=world_list)


@bp.route("/view/worlds/<wid>", methods=["GET"])
@login_required
def view_world(wid: elements.WorldID):
    """
    View a world
    """
    world = elements.loadWorld(get_db(), wid)
    if world is None:
        return "World not found", 404

    worlds = elements.listWorlds(get_db())
    (pworld, nworld) = elements.getAdjacentElements(world.getIdName(), worlds)

    characters = elements.listCharacters(get_db(), world.getID())
    char_list = []
    for entry in characters:
        char_id = entry.getID()
        char_name = entry.getName()
        character = elements.loadCharacter(get_db(), char_id)
        if character is not None:
            char_list.append((char_id, char_name, character.getDescription()))

    items = elements.listItems(get_db(), world.getID())
    item_list = []
    for entry in items:
        item_id = entry.getID()
        item_name = entry.getName()
        item = elements.loadItem(get_db(), item_id)
        if item is not None:
            item_list.append((item_id, item_name, item.getDescription()))

    sites = elements.listSites(get_db(), world.getID())
    site_list = []
    for entry in sites:
        site_id = entry.getID()
        site_name = entry.getName()
        site = elements.loadSite(get_db(), site_id)
        if site is not None:
            site_list.append((site_id, site_name, site.getDescription()))

    return flask.render_template(
            "view_world.html",
            world=world,
            character_list=char_list,
            item_list=item_list,
            site_list=site_list,
            pworld=pworld,
            nworld=nworld,
        )


@bp.route("/view/worlds/<wid>/characters/<eid>", methods=["GET"])
@login_required
def view_character(wid: elements.WorldID, eid: elements.ElemID):
    """
    View a character
    """
    world = elements.loadWorld(get_db(), wid)
    if world is None:
        return "World not found", 404
    character = elements.loadCharacter(get_db(), eid)
    if character is None:
        return "Character not found", 404
    characters = elements.listCharacters(get_db(), wid)
    (pchar, nchar) = elements.getAdjacentElements(character.getIdName(), characters)

    return flask.render_template(
            "view_character.html",
            world=world,
            character=character,
            pchar=pchar,
            nchar=nchar,
        )


@bp.route("/view/worlds/<wid>/items/<eid>", methods=["GET"])
@login_required
def view_item(wid: elements.WorldID, eid: elements.ElemID):
    """
    View a character
    """
    world = elements.loadWorld(get_db(), wid)
    if world is None:
        return "World not found", 404
    item = elements.loadItem(get_db(), eid)
    if item is None:
        return "Item not found", 404
    items = elements.listItems(get_db(), wid)
    (pitem, nitem) = elements.getAdjacentElements(item.getIdName(), items)

    return flask.render_template(
            "view_item.html", world=world, item=item, nitem=nitem, pitem=pitem
        )


@bp.route("/view/worlds/<wid>/sites/<eid>", methods=["GET"])
@login_required
def view_site(wid: elements.WorldID, eid: elements.ElemID):
    """
    View a site
    """
    world = elements.loadWorld(get_db(), wid)
    if world is None:
        return "World not found", 404
    site = elements.loadSite(get_db(), eid)
    if site is None:
        return "Site not found", 404
    sites = elements.listSites(get_db(), wid)
    (psite, nsite) = elements.getAdjacentElements(site.getIdName(), sites)

    return flask.render_template(
            "view_site.html", world=world, site=site, psite=psite, nsite=nsite
        )


@bp.route("/images/<iid>", methods=["GET"])
@login_required
def get_image(iid: elements.ElemID):
    """
    Return an image
    """
    image = elements.getImage(get_db(), iid)
    if image is None:
        return "Image not found", 404

    image_file = os.path.join(current_app.instance_path, image.filename)
    if not os.path.isfile(image_file):
        return "Image file not found", 404
    return flask.send_file(image_file, mimetype="image/webp")


@bp.route("/images/<iid>/thumb", methods=["GET"])
@login_required
def get_image_thumb(iid: elements.ElemID):
    """
    Return an image
    """
    image = elements.getImage(get_db(), iid)
    if image is None:
        return "Image not found", 404

    image_file = os.path.join(current_app.instance_path, image.getThumbName())
    if not os.path.isfile(image_file):
        return "Image file not found", 404
    return flask.send_file(image_file, mimetype="image/webp")


def get_user_id() -> str:
    """
    Return an ID for the current session.
    Create one if needed.
    """
    return g.user_id

@bp.route("/api/design_chat", methods=["GET", "POST"])
@auth_required
def design_chat_api():
    """
    Chat interface
    """
    user_id = get_user_id()
    chat_session = design_chat.DesignChatSession.loadChatSession(get_db(), user_id)
    deleteSession = False

    if request.method == "GET":
        content = chat_session.chat_history().model_dump()
    else:
        command = request.json.get("command")
        if command == "start":
            user_msg = request.json.get("user")
            view = request.json.get("view")
            chat_session.set_view(get_db(), view)
            reply = chat_session.chat_start(get_db(), user_msg)
            content = reply.model_dump()

        elif command == "continue":
            msg_id = request.json.get("id")
            reply = chat_session.chat_continue(get_db(), msg_id)
            logging.info("design chat updates: %s", reply.chat_response.updates)
            content = reply.model_dump()

        elif request.json.get("command") == "clear":
            content = {"status": "ok"}
            deleteSession = True
        else:
            content = {"error": "malformed input"}

    if not deleteSession:
        chat_session.saveChatSession(get_db())
    else:
        chat_session.deleteChatSession(get_db())
    return flask.jsonify(content)


@bp.route("/api/design_chat/view", methods=["GET"])
@auth_required
def design_chat_view_api():
    """
    Get / set current view for design chat.
    """
    user_id = get_user_id()
    chat_session = design_chat.DesignChatSession.loadChatSession(get_db(), user_id)
    content = {"view": chat_session.get_view()}
    return flask.jsonify(content)

@bp.route("/api/initdata", methods=["GET"])
@auth_required
def get_init_data():
    """
    Initial load of information for clients
    """
    # Returns session id and world id last loaded
    user_id = get_user_id()
    world_id = session.get("world_id", "")

    return {"user_id": user_id, "world_id": world_id}


@bp.route("/api/worlds", methods=["GET"])
@auth_required
def worlds_list():
    """
    API to access worldlist
    """
    world_list = []
    worlds = elements.listWorlds(get_db())
    for entry in worlds:
        wid = entry.getID()
        world = elements.loadWorld(get_db(), wid)
        image_prop = getElementThumbProperty(world)
        world_list.append(
            {
                "id": wid,
                "name": world.getName(),
                "description": world.getDescription(),
                "image": image_prop,
            }
        )

    return flask.jsonify(world_list)


@bp.route("/api/worlds/<wid>", methods=["GET"])
@auth_required
def worlds_api(wid):
    """
    API to access a world
    """
    world = elements.loadWorld(get_db(), wid)
    if world == None:
        return {"error", "World not found"}, 404

    images = getElementImageProps(world)
    result = world.getAllProperties()

    # Translate start conditions to a readable form
    start_conditions: list[str] = []
    for entry in world.startConditions():
        value = elements.Condition.getStrVal(get_db(), entry)
        if value is not None and len(value) > 0:
            start_conditions.append(value)
    
    result["start_conditions"] = start_conditions
    result["images"] = images

    return result


def getElementThumbProperty(element):
    """
    Return a property referencing an image for an element
    """
    # May be None
    image_id = element.getImageByIndex(0)
    if image_id is None:
        url = flask.url_for("static", filename="question-square-fill.svg")
        image_prop = {"id": "0", "url": url}
    else:
        image_prop = {
            "id": image_id,
            "url": flask.url_for("worldai.get_image_thumb", iid=image_id),
        }
    return image_prop


def getElementImageProps(element):
    images = []
    for image in element.getImages():
        url = flask.url_for("worldai.get_image", iid=image)
        images.append({"id": image, "url": url})

    if len(images) == 0:
        url = flask.url_for("static", filename="question-square-fill.svg")
        images.append({"id": "0", "url": url})
    return images


@bp.route("/api/worlds/<wid>/characters", methods=["GET"])
@auth_required
def characters_list(wid):
    """
    API to get the list of characters for a world
    """
    character_list = []
    world = elements.loadWorld(get_db(), wid)
    if world is None:
        return {"error", "World not found"}, 404
    characters = elements.listCharacters(get_db(), wid)

    for entry in characters:
        cid = entry.getID()
        character = elements.loadCharacter(get_db(), cid)
        image_prop = getElementThumbProperty(character)

        character_list.append(
            {
                "id": cid,
                "name": character.getName(),
                "description": character.getDescription(),
                "image": image_prop,
            }
        )

    return flask.jsonify(character_list)


@bp.route("/api/worlds/<wid>/characters/instances", methods=["GET"])
@auth_required
def characters_inst_list(wid):
    """
    API to get the list of characters for a world
    """
    # Save last opened in session
    session["world_id"] = wid

    character_list = []
    user_id = get_user_id()
    world = elements.loadWorld(get_db(), wid)
    if world is None:
        return {"error", "World not found"}, 404
    wstate_id = world_state.getWorldStateID(get_db(), user_id, wid)
    wstate = world_state.loadWorldState(get_db(), wstate_id)
    characters = elements.listCharacters(get_db(), wid)

    for entry in characters:
        cid = entry.getID()
        character = elements.loadCharacter(get_db(), cid)
        image_prop = getElementThumbProperty(character)

        character_list.append(
            {
                "id": cid,
                "name": character.getName(),
                "description": character.getDescription(),
                "givenSupport": wstate.getFriendship(id) > 0,
                "image": image_prop,
            }
        )

    return flask.jsonify(character_list)


@bp.route("/api/worlds/<wid>/characters/<cid>", methods=["GET"])
@auth_required
def characters_api(wid, cid):
    """
    API to access a character
    """
    character = elements.loadCharacter(get_db(), cid)
    if character == None or character.parent_id != wid:
        return {"error", "Character not found"}, 404

    images = getElementImageProps(character)
    result = character.getAllProperties()
    result["images"] = images

    return result


@bp.route("/api/worlds/<wid>/characters/<cid>/instance", methods=["GET"])
@auth_required
def character_stats(wid, cid):
    """
    API to get character status
    """
    user_id = get_user_id()
    world = elements.loadWorld(get_db(), wid)
    if world is None:
        return {"error", "World not found"}, 404
    # Save last opened in session
    session["world_id"] = wid

    wstate_id = world_state.getWorldStateID(get_db(), user_id, wid)
    wstate = world_state.loadWorldState(get_db(), wstate_id)

    character_data = client.LoadCharacterData(get_db(), wstate, cid)
    response = character_data.model_dump()
    return response


@bp.route("/api/worlds/<wid>/documents")
@auth_required
def doc_list_api(wid: elements.WorldID):
    """
    Return a list of documents for the world
    """
    if elements.loadWorld(get_db(), wid) is None:
        return Response({"error", "World not found"}, 404)
    doc_list = []
    for entry in elements.listDocuments(get_db(), wid):
        doc_list.append(entry.getJSON())
    return doc_list


@bp.route("/api/worlds/<wid>/documents/<did>")
@auth_required
def docs_api(wid: elements.WorldID, did: elements.ElemID):
    if elements.loadWorld(get_db(), wid) is None:
        return Response({"error", "World not found"}, 404)
    doc = elements.loadDocument(get_db(), did)
    if doc is None:
        return Response({"error", "Document not found"}, 404)
    sections = []
    for heading in doc.getSectionList():
        text = doc.getSectionText(heading)
        if text is not None:
            sections.append({"heading": heading, "text": text})
    return {"name": doc.getName(), "sections": sections}


@bp.route("/api/worlds/<wid>/sites", methods=["GET"])
@auth_required
def site_list_api(wid):
    """
    Get a list of sites
    """
    # Save last opened in session
    world = elements.loadWorld(get_db(), wid)
    if world is None:
        return {"error", "World not found"}, 404

    site_list = []
    sites = elements.listSites(get_db(), wid)

    for entry in sites:
        sid = entry.getID()
        site = elements.loadSite(get_db(), sid)
        image_prop = getElementThumbProperty(site)

        site_list.append(
            {
                "id": sid,
                "name": site.getName(),
                "description": site.getDescription(),
                "image": image_prop,
            }
        )
    return site_list


@bp.route("/api/worlds/<wid>/sites/instances", methods=["GET"])
@auth_required
def site_instances_list(wid):
    """
    Get a list of sites
    """
    world = elements.loadWorld(get_db(), wid)
    if world is None:
        return {"error", "World not found"}, 404

    # Save last opened in session
    session["world_id"] = wid

    site_list = []
    user_id = get_user_id()
    wstate_id = world_state.getWorldStateID(get_db(), user_id, wid)
    wstate = world_state.loadWorldState(get_db(), wstate_id)
    sites = elements.listSites(get_db(), wid)

    for entry in sites:
        sid = entry.getID()
        site = elements.loadSite(get_db(), sid)
        image_prop = getElementThumbProperty(site)
        site_list.append(
            {
                "id": sid,
                "name": site.getName(),
                "description": site.getDescription(),
                "open": wstate.isSiteOpen(sid),
                "image": image_prop,
            }
        )
    return site_list


@bp.route("/api/worlds/<wid>/sites/<sid>", methods=["GET"])
@auth_required
def site_api(wid, sid):
    """
    API to load a site
    """
    world = elements.loadWorld(get_db(), wid)
    if world is None:
        return {"error", "World not found"}, 404
    site = elements.loadSite(get_db(), sid)
    if site == None:
        return {"error", "Site not found"}, 404

    images = getElementImageProps(site)
    result = site.getAllProperties()
    result["images"] = images

    return result


@bp.route("/api/worlds/<wid>/sites/<sid>/instance", methods=["GET"])
@auth_required
def site_instance(wid, sid):
    """
    API to load info and state for a site
    """
    user_id = get_user_id()
    world = elements.loadWorld(get_db(), wid)
    if world is None:
        return {"error", "World not found"}, 404
    # Save last opened in session
    session["world_id"] = wid

    wstate_id = world_state.getWorldStateID(get_db(), user_id, wid)
    wstate = world_state.loadWorldState(get_db(), wstate_id)
    site = elements.loadSite(get_db(), sid)
    if site == None:
        return {"error", "Site not found"}, 404

    chat_char_id = wstate.getChatCharacter()
    images = getElementImageProps(site)
    result = site.getAllProperties()
    result["images"] = images

    characters = []
    cid_list = wstate.getCharactersAtLocation(sid)
    for cid in cid_list:
        character = elements.loadCharacter(get_db(), cid)
        if character is None:
            continue
        # TODO: make more DRY
        image_prop = getElementThumbProperty(character)
        record = {
            "id": cid,
            "name": character.getName(),
            "description": character.getDescription(),
            "givenSupport": wstate.getFriendship(cid) > 0,
            "image": image_prop,
        }
        characters.append(record)

    result["characters"] = characters

    items = []
    iid_list = wstate.getItemsAtLocation(sid)
    for iid in iid_list:
        item = elements.loadItem(get_db(), iid)
        # TODO: make more DRY
        image_prop = getElementThumbProperty(item)
        items.append(
            {
                "id": iid,
                "name": item.getName(),
                "description": item.getDescription(),
                "mobile": item.getIsMobile(),
                "image": image_prop,
            }
        )
    result["items"] = items

    return result


@bp.route("/api/worlds/<wid>/items", methods=["GET"])
@auth_required
def items_list(wid):
    """
    API to get the items for a world
    """
    item_list = []
    world = elements.loadWorld(get_db(), wid)
    if world is None:
        return {"error", "World not found"}, 404
    items = elements.listItems(get_db(), wid)

    for entry in items:
        iid = entry.getID()
        item = elements.loadItem(get_db(), iid)
        image_prop = getElementThumbProperty(item)

        item_list.append(
            {
                "id": iid,
                "name": item.getName(),
                "description": item.getDescription(),
                "ability": elements.getItemAbilityDescription(get_db(), item),
                "image": image_prop,
            }
        )

    return item_list


@bp.route("/api/worlds/<wid>/items/instances", methods=["GET"])
@auth_required
def items_intances_list(wid):
    """
    API to get the items instances for a world
    """
    item_list = []
    user_id = get_user_id()
    world = elements.loadWorld(get_db(), wid)
    if world is None:
        return {"error", "World not found"}, 404
    # Save last opened in session
    session["world_id"] = wid

    wstate_id = world_state.getWorldStateID(get_db(), user_id, wid)
    wstate = world_state.loadWorldState(get_db(), wstate_id)
    items = elements.listItems(get_db(), wid)

    for entry in items:
        iid = entry.getID()
        item = elements.loadItem(get_db(), iid)
        image_prop = getElementThumbProperty(item)
        
        item_list.append(
            {
                "id": iid,
                "name": item.getName(),
                "description": item.getDescription(),
                "ability": elements.getItemAbilityDescription(get_db(), item),
                "have_item": wstate.hasItem(iid),
                "image": image_prop,
            }
        )

    return item_list


@bp.route("/api/worlds/<wid>/items/<iid>", methods=["GET"])
@auth_required
def item_api(wid, iid):
    """
    API to access an item
    """
    item = elements.loadItem(get_db(), iid)
    if item == None or item.parent_id != wid:
        return {"error", "Item not found"}, 404

    images = getElementImageProps(item)
    result = item.getAllProperties()
    result["images"] = images
    image_prop = getElementThumbProperty(item)
    result["image"] = image_prop

    # Include site name if needed
    if len(item.getAbility().site_id) > 0:
        site = elements.loadSite(get_db(), item.getAbility().site_id)
        if site is not None:
            result["ability"]["site"] = site.getName()

    return result


@bp.route("/api/worlds/<wid>/items/<iid>/instance", methods=["GET"])
@auth_required
def item_instance(wid, iid):
    """
    API to access an item instance
    """
    user_id = get_user_id()
    item = elements.loadItem(get_db(), iid)
    if item == None or item.parent_id != wid:
        return {"error", "Item not found"}, 404
    # Save last opened in session
    session["world_id"] = wid

    wstate_id = world_state.getWorldStateID(get_db(), user_id, wid)
    wstate = world_state.loadWorldState(get_db(), wstate_id)

    images = getElementImageProps(item)
    result = item.getAllProperties()
    result["images"] = images
    image_prop = getElementThumbProperty(item)
    result["image"] = image_prop
    result["location"] = wstate.getItemLocation(iid)

    # Include site name if needed
    if len(item.getAbility().site_id) > 0:
        site = elements.loadSite(get_db(), item.getAbility().site_id)
        if site is not None:
            result["ability"]["site"] = site.getName()

    return result


@bp.route("/api/worlds/<wid>/command", methods=["POST"])
@auth_required
def command_api(wid):
    """
    API to make player changes

    Returns a client_command.CommandResponse: (message, status, changed)
    """
    user_id = get_user_id()
    world = elements.loadWorld(get_db(), wid)
    if world is None:
        return {"error", "World not found"}, 404
    wstate_id = world_state.getWorldStateID(get_db(), user_id, wid)
    wstate = world_state.loadWorldState(get_db(), wstate_id)

    command = client_commands.Command(**request.json)
    logging.info("commmand name %s", command.name)
    logging.info("location: %s", wstate.getLocation())
    client_actions = client_commands.ClientActions(get_db(), world, wstate, "Travler")
    # TODO: make this return include a WorldStatus
    response = client_actions.ExecCommand(command)

    if response.world_status.changed:
        logging.info("COMMAND: save world state")
        world_state.saveWorldState(get_db(), wstate)

    return response.model_dump()


@bp.route("/api/worlds/<wid>/instance", methods=["GET", "POST"])
@auth_required
def state(wid):
    """
    Load and return the world status
    """
    user_id = get_user_id()
    world = elements.loadWorld(get_db(), wid)
    if world is None:
        return {"error", "World not found"}, 404
    wstate_id = world_state.getWorldStateID(get_db(), user_id, wid)

    if request.method == "GET":
        wstate = world_state.loadWorldState(get_db(), wstate_id)
        response = client.WorldStatus()
        client.update_world_status(get_db(), wstate, response)
        return response.model_dump()

    logging.info("Reset game %s:%s:%s", user_id, world.getID(), wstate_id)
    world_state.clearWorldState(get_db(), wstate_id)

    return { "status": "ok"}, 200


@bp.route("/api/worlds/<wid>/characters/<cid>/thread", methods=["GET", "POST"])
@auth_required
def thread_api(wid, cid):
    """
    Character chat interface
    Returns a:
    - character_chat.CharacterChatResponse
    or
    - character_chat.CharacterHistoryResponse
    """
    user_id = get_user_id()
    character = elements.loadCharacter(get_db(), cid)
    world = elements.loadWorld(get_db(), wid)
    if character is None or world is None:
        return {"error", "World not found"}, 404

    wstate_id = world_state.getWorldStateID(get_db(), user_id, wid)
    # TODO: this is where we need lock for updating
    chat_session = character_chat.CharacterChat.loadChatSession(
        get_db(), wstate_id, wid, cid
    )
    content = None
    if request.method == "GET":
        history_response = chat_session.chat_history(get_db())
        content = history_response.model_dump()
    else:
        command = request.json.get("command")
        if command == "start":
            user_msg = request.json.get("user")
            result = chat_session.chat_start(get_db(), user_msg)
            content = result.model_dump()

        elif command == "continue":
            msg_id = request.json.get("id")
            reply = chat_session.chat_continue(get_db(), msg_id)
            content = reply.model_dump()

    # TODO: make this return include a WorldStatus
    if content is None:
        content = {"error": "malformed input"}

    chat_session.saveChatSession(get_db())
    return content


@bp.route("/api/worlds/<wid>/characters/<cid>/action", methods=["POST"])
@auth_required
def action_api(wid, cid):
    """
    Action with character

    Combination use artifact with a character chat.

    Returns an extended character_chat.CharacterChatResponse
    Includes:
      - result.world_status.response_message   (message): message generated by the action
      - result.world_status.changed  (changed): state of the world changed as a result
      - result.chat_response.chat_enabled  (enabled): user can continue to chat with character
    """
    user_id = get_user_id()
    character = elements.loadCharacter(get_db(), cid)
    world = elements.loadWorld(get_db(), wid)
    if character is None or world is None:
        return {"error", "World not found"}, 404


    command = request.json.get("command")
    if command == None:
        return {"error", "missing arguments"}, 400

    wstate_id = world_state.getWorldStateID(get_db(), user_id, wid)
    chat_session = character_chat.CharacterChat.loadChatSession(
        get_db(), wstate_id, wid, cid
    )

    # Run event - ok to call will an empty event
    if command == "start":
        action = request.json.get("action")
        item_id = request.json.get("item")
        if action == None or item_id == None:
            return {"error", "missing arguments"}, 400

        character = elements.loadCharacter(get_db(), cid)
        item = elements.loadItem(get_db(), item_id)
        if item is None or character is None:
            return {"error", "Element not found"}, 404

        # Perform action
        wstate = world_state.loadWorldState(get_db(), wstate_id)

        client_actions = client_commands.ClientActions(get_db(), world, wstate, "Travler")
        if action == "use":
            # Run the use command
            world_status = client_actions.UseItemCharacter(item, character)
        elif action == "drop":
            # Run the drop item command
            # Note: this is currently not used. Instead wstate.character_event is used on a drop
            world_status = client_actions.DropItem(item_id, item)

        if world_status.changed:
            # Save state since chat functions may load it again
            world_state.saveWorldState(get_db(), wstate)

        reply = chat_session.chat_event_start(get_db(), world_status.last_event)
        
        # Copy results from command action into resonse
        # TODO: just copy entire world_status?
        reply.world_status.changed = world_status.changed
        reply.world_status.response_message = world_status.response_message
        reply.world_status.last_event = world_status.last_event
        content = reply.model_dump()

    elif command == "continue":
        msg_id = request.json.get("id")
        reply = chat_session.chat_continue(get_db(), msg_id)
        content = reply.model_dump()

    chat_session.saveChatSession(get_db())

    return content
