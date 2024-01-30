"""
Test Client Command Functions

Integration test
"""
from worldai import elements
from worldai import db_access
from worldai import world_state
from worldai import client_commands

class Environment:
  def __init__(self, db, world, wstate):
    self.db = db
    self.world = world
    self.wstate = wstate

  @staticmethod
  def get_env(app):
    db = db_access.open_db()  
    assert db is not None
    worlds = elements.listWorlds(db)
    world_id = worlds[0].id
    assert world_id is not None
    session_id = "1234"
    world = elements.loadWorld(db, world_id)
    assert world is not None
    wstate_id = world_state.getWorldStateID(db, session_id, world_id)
    wstate = world_state.loadWorldState(db, wstate_id)
    assert wstate is not None
    return Environment(db, world, wstate)
    
  
def test_access_app(app):
  env = Environment.get_env(app)

def test_go_command(app):
  env = Environment.get_env(app)
  command = { "name": "go",
              "to": "id123" };

  # Non-existant site
  command = client_commands.Command(**command)
  client_actions = client_commands.ClientActions(env.db, env.world, env.wstate)
  response = client_actions.ExecCommand(command)

  # Real site
  sites = elements.listSites(env.db, env.world.id)
  command.to = sites[0].id
  client_actions = client_commands.ClientActions(env.db, env.world, env.wstate)
  response = client_actions.ExecCommand(command)

  # No site
  sites = elements.listSites(env.db, env.world.id)
  command.to = None
  client_actions = client_commands.ClientActions(env.db, env.world, env.wstate)
  response = client_actions.ExecCommand(command)

  
def test_take_command(app):
  env = Environment.get_env(app)
  command = { "name": "take",
              "item": "id123" };

  # Non existant item
  command = client_commands.Command(**command)
  client_actions = client_commands.ClientActions(env.db, env.world, env.wstate)
  response = client_actions.ExecCommand(command)

  # Real item - diff location
  sites = elements.listSites(env.db, env.world.id)
  site_id1 = sites[0].id
  site_id2 = sites[1].id  
  items = elements.listItems(env.db, env.world.id)
  item_id = items[0].id
  
  env.wstate.setItemLocation(item_id, site_id1)
  env.wstate.setLocation(site_id2)

  command.item = item_id
  response = client_actions.ExecCommand(command)
  assert not response.changed

  env.wstate.setItemLocation(item_id, site_id2)
  response = client_actions.ExecCommand(command)
  assert response.changed

  
def test_select_command(app):
  env = Environment.get_env(app)
  command = { "name": "select",
              "item": "id123" };

  # Non-existant item
  command = client_commands.Command(**command)
  client_actions = client_commands.ClientActions(env.db, env.world, env.wstate)
  response = client_actions.ExecCommand(command)
  assert not response.changed

  # Real item, do not have
  sites = elements.listSites(env.db, env.world.id)
  site_id = sites[0].id
  items = elements.listItems(env.db, env.world.id)
  item_id = items[0].id

  command.item = item_id
  client_actions = client_commands.ClientActions(env.db, env.world, env.wstate)
  response = client_actions.ExecCommand(command)
  assert not response.changed
  
  # Real item, do have
  env.wstate.setLocation(site_id)
  env.wstate.setItemLocation(item_id, site_id)
  env.wstate.addItem(item_id)  
  client_actions = client_commands.ClientActions(env.db, env.world, env.wstate)
  response = client_actions.ExecCommand(command)
  assert response.changed

def test_enage_command(app):
  env = Environment.get_env(app)
  command = { "name": "engage",
              "character": "id123" };

  # Non existant character
  command = client_commands.Command(**command)
  client_actions = client_commands.ClientActions(env.db, env.world, env.wstate)
  response = client_actions.ExecCommand(command)
  assert not response.changed
  
  # Real character, wrong location
  site_id = elements.listSites(env.db, env.world.id)[0].id
  cid = elements.listCharacters(env.db, env.world.id)[0].id
  command.character = cid
  
  env.wstate.setCharacterLocation(cid, site_id)
  response = client_actions.ExecCommand(command)
  assert not response.changed

  # Real character, right location
  env.wstate.setLocation(site_id)
  response = client_actions.ExecCommand(command)
  assert response.changed

  

def test_disenage_command(app):
  env = Environment.get_env(app)
  command = { "name": "disengage",
              "character": "id123" };

  # Not existant character
  command = client_commands.Command(**command)
  client_actions = client_commands.ClientActions(env.db, env.world, env.wstate)
  response = client_actions.ExecCommand(command)
  assert response.changed

  # Real character, not engaged
  site_id = elements.listSites(env.db, env.world.id)[0].id
  cid = elements.listCharacters(env.db, env.world.id)[0].id
  env.wstate.setLocation(site_id)
  env.wstate.setCharacterLocation(cid, site_id)
  command.character = cid
  response = client_actions.ExecCommand(command)  
  assert response.changed

  # Real character, enaged
  command.name = "engage"
  response = client_actions.ExecCommand(command)
  assert response.changed
  command.name = "disengage"
  response = client_actions.ExecCommand(command)
  assert response.changed
  
  
def test_use_command(app):
  env = Environment.get_env(app)
  command = { "name": "use",
              "item": "id123" };

  # Not real item
  command = client_commands.Command(**command)
  client_actions = client_commands.ClientActions(env.db, env.world, env.wstate)
  response = client_actions.ExecCommand(command)
  assert not response.changed

  item_id = elements.listItems(env.db, env.world.id)[0].id

  # Real item - don't have
  command.item = item_id
  response = client_actions.ExecCommand(command)
  assert not response.changed
  
  # Real item - have, not selected
  # If item is not mobile, still works, but not great test coverage here
  env.wstate.addItem(item_id)
  response = client_actions.ExecCommand(command)
  assert response.changed

  

def test_use_character(app):
  env = Environment.get_env(app)
  

  
