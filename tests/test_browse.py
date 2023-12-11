"""
Test the basics in the HTML interface.
TODO:
 - add create world, test access to world
 - same with character, site, item
"""


def do_login(client, app):
  """
  Post auth  key to the login page.
  Will get a session cookie that enables access.
  """
  response = client.post("/login", data={
    "auth_key": app.config['AUTH_KEY'],
    })
  assert response.status_code == 302
  assert response.location == '/'
  

def test_no_login(client):
  # No login
  response = client.get("/")
  assert response.status_code == 302
  assert response.location == '/login'


def test_login(client, app):
  do_login(client, app)
  response = client.get("/")
  assert response.status_code == 200
  assert b"<h2>" in response.data

def test_client_no_login(client, app):
  response = client.get("/client")
  assert response.status_code == 302

def test_client_login(client, app):
  do_login(client, app)  
  response = client.get("/client")
  assert response.status_code == 200

def test_view_worlds(client, app):
  do_login(client, app)
  response = client.get("/view/worlds")
  assert response.status_code == 200
  assert b"<h1>" in response.data
  assert not b"<h2>" in response.data

def test_view_world(client, app):
  do_login(client, app)
  response = client.get("/view/worlds/123")
  assert response.status_code == 400
  assert b"World not found" in response.data

def test_view_character(client, app):
  do_login(client, app)
  response = client.get("/view/worlds/123/characters/456")
  assert response.status_code == 400
  assert b"World not found" in response.data


def test_view_items(client, app):
  do_login(client, app)
  response = client.get("/view/worlds/123/items/456")
  assert response.status_code == 400
  assert b"World not found" in response.data

def test_view_site(client, app):
  do_login(client, app)
  response = client.get("/view/worlds/123/sites/456")
  assert response.status_code == 400
  assert b"World not found" in response.data
  
  
  
  
  
