"""
Test the basics of the JSON APIs
"""
import json

def test_no_access(client):
  response = client.get("/api/design_chat")
  assert response.status_code == 401

def bearer_token(app):
  return "Bearer " + app.config['AUTH_KEY']

def test_world_chars(client, app):
  response = client.get("/api/worlds",
                       headers= {
                         "Authorization": bearer_token(app)})
  assert response.status_code == 200
  assert len(response.json) > 0
  world_id = response.json[0]["id"]

  response = client.get(f"/api/worlds/{world_id}",
                        headers= {
                          "Authorization": bearer_token(app)})
  assert response.status_code == 200
  assert len(response.json) > 0

  response = client.get(f"/api/worlds/{world_id}/characters",
                        headers= {
                          "Authorization": bearer_token(app)})
  assert response.status_code == 200
  assert len(response.json) > 0
  id = response.json[0]["id"]

  response = client.get(f"/api/worlds/{world_id}/characters/{id}",
                        headers= {
                          "Authorization": bearer_token(app)})
  assert response.status_code == 200
  assert id == response.json["id"]

  response = client.get(f"/api/worlds/{world_id}/sites",
                        headers= {
                          "Authorization": bearer_token(app)})
  assert response.status_code == 200
  assert len(response.json) > 0
  id = response.json[0]["id"]

  response = client.get(f"/api/worlds/{world_id}/sites/{id}",
                        headers= {
                          "Authorization": bearer_token(app)})
  assert response.status_code == 200
  assert id == response.json["id"]
  

def test_character_chat(client, app):
  response = client.get("/api/worlds",
                       headers= {
                         "Authorization": bearer_token(app)})
  world_id = response.json[0]["id"]
  response = client.get(f"/api/worlds/{world_id}/characters",
                        headers= {
                          "Authorization": bearer_token(app)})
  char_id = response.json[0]["id"]

  # Post chat
  response = client.post(f"/api/threads/worlds/{world_id}/characters/{char_id}",
                         headers={
                           'Content-Type': 'application/json',
                           "Authorization": bearer_token(app),
                         },
                         json={
                           "user": "hi there!",
                         })
  assert response.status_code == 200
  assert response.json["id"] is not None


  # Get chat history
  response = client.get(f"/api/threads/worlds/{world_id}/characters/{char_id}",
                        headers= {
                          "Authorization": bearer_token(app)})
  assert response.status_code == 200
  assert len(response.json) > 0


def test_chat_get(client, app):
  response = client.get("/api/design_chat", headers={
    "Authorization": bearer_token(app),
  })
  assert response.status_code == 200
  assert response.json['view'] is not None
  assert len(response.json['messages']) == 0
  
  response = client.get(f"/api/design_chat", headers={
    "Authorization": bearer_token(app),
  })
  assert response.status_code == 200
  assert response.json['view'] is not None
  assert len(response.json['messages']) == 0
  
  response = client.post(f"/api/design_chat",
                         headers={
                           'Content-Type': 'application/json',
                           "Authorization": bearer_token(app),
                         },
                         json={
                           "user": "hi there!",
                         })
  assert response.status_code == 200
  
  response = client.get(f"/api/design_chat", headers={
    "Authorization": bearer_token(app),
  })
  assert response.status_code == 200
  assert response.json['view'] is not None
  assert len(response.json['messages']) > 0

  
def test_chat_post(client, app):
  response = client.post("/api/design_chat",
                         headers={
                           'Content-Type': 'application/json',
                           "Authorization": bearer_token(app),
                         },
                         json={
                           "user": "hi there!",
                         })
  assert response.status_code == 200
  assert response.json['reply'] is not None
  assert not response.json['changes']
  assert response.json['view'] is not None
  

def test_chat_cmd_clear(client, app):
  response = client.post(f"/api/design_chat",
                         headers={
                           'Content-Type': 'application/json',
                           "Authorization": bearer_token(app),
                         },
                         json={
                           "user": "hi there!",
                         })
  assert response.status_code == 200

  
  response = client.get(f"/api/design_chat", headers={
    "Authorization": bearer_token(app),
  })
  assert response.status_code == 200
  assert len(response.json['messages']) > 0
  
  response = client.post(f"/api/design_chat",
                         headers={
                           'Content-Type': 'application/json',
                           "Authorization": bearer_token(app),
                         },
                         json={
                           "command": "clear_thread",
                         })
  assert response.status_code == 200
  assert response.json['status'] == "ok"

  response = client.get(f"/api/design_chat", headers={
    "Authorization": bearer_token(app),
  })
  assert response.status_code == 200
  assert len(response.json['messages']) == 0

  
  
