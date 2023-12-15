"""
Test the basics of the JSON APIs
"""
import json

def test_no_access(client):
  response = client.get("/chat/ses123")
  assert response.status_code == 401
  response = client.post("/chat/ses123")
  assert response.status_code == 401
  response = client.post("/view_props")
  assert response.status_code == 401

def bearer_token(app):
  return "Bearer " + app.config['AUTH_KEY']

thread="43998a028378e5df81c12b69"

def test_chat_get(client, app):
  response = client.get("/chat/123", headers={
    "Authorization": bearer_token(app),
  })
  assert response.status_code == 200
  assert response.json['view'] is not None
  assert len(response.json['messages']) == 0
  
  response = client.get(f"/chat/{thread}", headers={
    "Authorization": bearer_token(app),
  })
  assert response.status_code == 200
  assert response.json['view'] is not None
  assert len(response.json['messages']) > 0

  
def test_chat_post(client, app):
  response = client.post("/chat/123",
                         headers={
                           'Content-Type': 'application/json',
                           "Authorization": bearer_token(app),
                         },
                         json={
                           "user": "hi there!",
                         })
  assert response.status_code == 200
  assert response.json['assistant'] is not None
  assert not response.json['changes']
  assert response.json['view'] is not None
  

def test_chat_cmd_clear(client, app):
  response = client.get(f"/chat/{thread}", headers={
    "Authorization": bearer_token(app),
  })
  assert response.status_code == 200
  assert len(response.json['messages']) > 0
  
  response = client.post(f"/chat/{thread}",
                         headers={
                           'Content-Type': 'application/json',
                           "Authorization": bearer_token(app),
                         },
                         json={
                           "command": "clear_thread",
                         })
  assert response.status_code == 200
  assert response.json['status'] == "ok"

  response = client.get(f"/chat/{thread}", headers={
    "Authorization": bearer_token(app),
  })
  assert response.status_code == 200
  assert len(response.json['messages']) == 0

  
  
def test_view_props(client, app):
  # List of workds
  response = client.post("/view_props",
                         headers={
                           'Content-Type': 'application/json',    
                           "Authorization": bearer_token(app),
                         },
                         json = {
                         })
  assert response.status_code == 200
  assert response.json["html"] is not None
  assert response.json["images"] is not None
  assert len(response.json["images"]) == 0

  # World
  response = client.post("/view_props",
                         headers={
                           'Content-Type': 'application/json',    
                           "Authorization": bearer_token(app),
                         },
                         json = {
                           "wid": "ida1ad7f2c",
                           "element_type": "World",
                           "id": "ida1ad7f2c",
                         })
  assert response.status_code == 200
  assert response.json["html"] is not None
  assert response.json["images"] is not None

  # Character
  response = client.post("/view_props",
                         headers={
                           'Content-Type': 'application/json',    
                           "Authorization": bearer_token(app),
                         },
                         json = {
                           "wid": "ida1ad7f2c",
                           "element_type": "Character",
                           "id": "id7b89a481",
                         })
  assert response.status_code == 200
  assert response.json["html"] is not None
  assert response.json["images"] is not None
  

  # Item
  response = client.post("/view_props",
                         headers={
                           'Content-Type': 'application/json',    
                           "Authorization": bearer_token(app),
                         },
                         json = {
                           "wid": "ida1ad7f2c",
                           "element_type": "Item",
                           "id": "id5936b090",
                         })
  assert response.status_code == 200
  assert response.json["html"] is not None
  assert response.json["images"] is not None

  # Site
  response = client.post("/view_props",
                         headers={
                           'Content-Type': 'application/json',    
                           "Authorization": bearer_token(app),
                         },
                         json = {
                           "wid": "ida1ad7f2c",
                           "element_type": "World",
                           "id": "id6c7f129d",
                         })
  assert response.status_code == 200
  assert response.json["html"] is not None
  assert response.json["images"] is not None
  
