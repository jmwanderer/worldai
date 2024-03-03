"""
Test the basics of the JSON APIs
"""

import json


def test_no_access(client):
    response = client.get("/api/design_chat")
    assert response.status_code == 401


def bearer_token(app):
    return "Bearer " + app.config["AUTH_KEY"]


def test_world_chars(client, app):
    response = client.get("/api/worlds", headers={"Authorization": bearer_token(app)})
    assert response.status_code == 200
    assert len(response.json) > 0
    world_id = response.json[0]["id"]

    response = client.get(
        f"/api/worlds/{world_id}", headers={"Authorization": bearer_token(app)}
    )
    assert response.status_code == 200
    assert len(response.json) > 0

    response = client.get(
        f"/api/worlds/{world_id}/characters",
        headers={"Authorization": bearer_token(app)},
    )
    assert response.status_code == 200
    assert len(response.json) > 0
    id = response.json[0]["id"]
    assert response.json[0].get("givenSupport") is None

    response = client.get(
        f"/api/worlds/{world_id}/characters/instances",
        headers={"Authorization": bearer_token(app)},
    )
    assert response.status_code == 200
    assert len(response.json) > 0
    id = response.json[0]["id"]
    assert response.json[0].get("givenSupport") is not None

    response = client.get(
        f"/api/worlds/{world_id}/characters/{id}",
        headers={"Authorization": bearer_token(app)},
    )
    assert response.status_code == 200
    assert id == response.json["id"]

    response = client.get(
        f"/api/worlds/{world_id}/sites", headers={"Authorization": bearer_token(app)}
    )
    assert response.status_code == 200
    assert len(response.json) > 0
    id = response.json[0]["id"]

    response = client.get(
        f"/api/worlds/{world_id}/sites/instances",
        headers={"Authorization": bearer_token(app)},
    )
    assert response.status_code == 200
    assert len(response.json) > 0
    id = response.json[0]["id"]

    response = client.get(
        f"/api/worlds/{world_id}/sites/{id}",
        headers={"Authorization": bearer_token(app)},
    )
    assert response.status_code == 200
    assert id == response.json["id"]
    assert response.json.get("items") is None

    response = client.get(
        f"/api/worlds/{world_id}/sites/{id}/instance",
        headers={"Authorization": bearer_token(app)},
    )
    assert response.status_code == 200
    assert id == response.json["id"]
    assert response.json.get("items") is not None

    response = client.get(
        f"/api/worlds/{world_id}/items", headers={"Authorization": bearer_token(app)}
    )
    assert response.status_code == 200
    assert len(response.json) > 0
    id = response.json[0]["id"]

    response = client.get(
        f"/api/worlds/{world_id}/items/instances",
        headers={"Authorization": bearer_token(app)},
    )
    assert response.status_code == 200
    assert len(response.json) > 0
    id = response.json[0]["id"]
    assert response.json[0].get("have_item") is not None

    response = client.get(
        f"/api/worlds/{world_id}/items/{id}",
        headers={"Authorization": bearer_token(app)},
    )
    assert response.status_code == 200
    assert id == response.json["id"]

    response = client.get(
        f"/api/worlds/{world_id}/items/{id}/instance",
        headers={"Authorization": bearer_token(app)},
    )
    assert response.status_code == 200
    assert id == response.json["id"]
    assert response.json["location"] is not None


def test_documents(client, app):
    response = client.get("/api/worlds", headers={"Authorization": bearer_token(app)})
    assert response.status_code == 200
    assert len(response.json) > 0
    world_id = response.json[0]["id"]

    response = client.get(
        f"api/worlds/{world_id}/documents", headers={"Authorization": bearer_token(app)}
    )
    assert response.status_code == 200
    assert len(response.json) > 0

    doc_id = response.json[0]["id"]

    response = client.get(
        f"api/worlds/{world_id}/documents/{doc_id}",
        headers={"Authorization": bearer_token(app)},
    )
    assert response.status_code == 200


def test_character_chat(client, app):
    response = client.get("/api/worlds", headers={"Authorization": bearer_token(app)})
    world_id = response.json[0]["id"]
    response = client.get(
        f"/api/worlds/{world_id}/characters",
        headers={"Authorization": bearer_token(app)},
    )
    char_id = response.json[0]["id"]

    # Post chat
    response = client.post(
        f"/api/worlds/{world_id}/characters/{char_id}/thread",
        headers={
            "Content-Type": "application/json",
            "Authorization": bearer_token(app),
        },
        json={
            "user": "hi there!",
            "command": "start",
        },
    )
    assert response.status_code == 200
    assert response.json["chat_response"]["id"] is not None

    # Get chat history
    response = client.get(
        f"/api/worlds/{world_id}/characters/{char_id}/thread",
        headers={"Authorization": bearer_token(app)},
    )
    assert response.status_code == 200
    assert len(response.json) > 0


def test_chat_get(client, app):
    response = client.get(
        "/api/design_chat",
        headers={
            "Authorization": bearer_token(app),
        },
    )
    assert response.status_code == 200
    assert response.json["view"] is not None
    assert len(response.json["history_response"]["messages"]) == 0

    response = client.get(
        f"/api/design_chat",
        headers={
            "Authorization": bearer_token(app),
        },
    )
    assert response.status_code == 200
    assert response.json["view"] is not None
    assert len(response.json["history_response"]["messages"]) == 0

    response = client.post(
        f"/api/design_chat",
        headers={
            "Content-Type": "application/json",
            "Authorization": bearer_token(app),
        },
        json={
            "command": "start",
            "user": "hi there!",
        },
    )
    assert response.json["chat_response"]["done"]
    assert response.status_code == 200

    response = client.get(
        f"/api/design_chat",
        headers={
            "Authorization": bearer_token(app),
        },
    )
    assert response.status_code == 200
    assert response.json["view"] is not None
    assert len(response.json["history_response"]["messages"]) > 0


def test_chat_post(client, app):
    response = client.post(
        "/api/design_chat",
        headers={
            "Content-Type": "application/json",
            "Authorization": bearer_token(app),
        },
        json={
            "command": "start",
            "user": "hi there!",
        },
    )
    assert response.status_code == 200
    assert response.json["chat_response"]["reply"] is not None
    assert not response.json["made_changes"]
    assert response.json["view"] is not None


def test_chat_cmd_clear(client, app):
    response = client.post(
        f"/api/design_chat",
        headers={
            "Content-Type": "application/json",
            "Authorization": bearer_token(app),
        },
        json={
            "command": "start",
            "user": "hi there!",
        },
    )
    assert response.status_code == 200

    response = client.get(
        f"/api/design_chat",
        headers={
            "Authorization": bearer_token(app),
        },
    )
    assert response.status_code == 200
    assert len(response.json["history_response"]["messages"]) > 0

    response = client.post(
        f"/api/design_chat",
        headers={
            "Content-Type": "application/json",
            "Authorization": bearer_token(app),
        },
        json={
            "command": "clear",
        },
    )
    assert response.status_code == 200
    assert response.json["status"] == "ok"

    response = client.get(
        f"/api/design_chat",
        headers={
            "Authorization": bearer_token(app),
        },
    )
    assert response.status_code == 200
    assert len(response.json["history_response"]["messages"]) == 0


def test_command(client, app):
    # /api/world/<wid>/command
    #  - go, take, engage, disengage
    response = client.get("/api/worlds", headers={"Authorization": bearer_token(app)})
    world_id = response.json[0]["id"]

    response = client.get(
        f"/api/worlds/{world_id}/sites", headers={"Authorization": bearer_token(app)}
    )
    assert response.status_code == 200
    assert len(response.json) > 0
    site_id = response.json[0]["id"]

    response = client.get(
        f"/api/worlds/{world_id}/characters",
        headers={"Authorization": bearer_token(app)},
    )
    assert response.status_code == 200
    assert len(response.json) > 0
    char_id = response.json[0]["id"]

    response = client.get(
        f"/api/worlds/{world_id}/items", headers={"Authorization": bearer_token(app)}
    )
    assert response.status_code == 200
    assert len(response.json) > 0
    item_id = response.json[0]["id"]

    response = client.post(
        f"/api/worlds/{world_id}/command",
        headers={
            "Content-Type": "application/json",
            "Authorization": bearer_token(app),
        },
        json={"name": "go", "to": site_id},
    )
    assert response.status_code == 200

    response = client.post(
        f"/api/worlds/{world_id}/command",
        headers={
            "Content-Type": "application/json",
            "Authorization": bearer_token(app),
        },
        json={"name": "engage", "character": char_id},
    )
    assert response.status_code == 200

    response = client.post(
        f"/api/worlds/{world_id}/command",
        headers={
            "Content-Type": "application/json",
            "Authorization": bearer_token(app),
        },
        json={
            "name": "disengage",
        },
    )
    assert response.status_code == 200

    response = client.post(
        f"/api/worlds/{world_id}/command",
        headers={
            "Content-Type": "application/json",
            "Authorization": bearer_token(app),
        },
        json={"name": "take", "item": item_id},
    )
    assert response.status_code == 200


def testLoadWorldStatus(client, app):
    response = client.get("/api/worlds", headers={"Authorization": bearer_token(app)})
    world_id = response.json[0]["id"]

    response = client.get(
        f"/api/worlds/{world_id}/status",
        headers={
            "Authorization": bearer_token(app),
        },
    )
    assert response.status_code == 200

    response = client.get(
        f"/api/worlds/{world_id}/status",
        headers={
            "Authorization": bearer_token(app),
        },
    )
    assert response.status_code == 200


def testLoadCharacterData(client, app):
    response = client.get("/api/worlds", headers={"Authorization": bearer_token(app)})
    world_id = response.json[0]["id"]

    response = client.get(
        f"/api/worlds/{world_id}/characters",
        headers={"Authorization": bearer_token(app)},
    )
    assert response.status_code == 200
    assert len(response.json) > 0
    id = response.json[0]["id"]

    response = client.get(
        f"/api/worlds/{world_id}/characters/{id}/instance",
        headers={
            "Authorization": bearer_token(app),
        },
    )
    assert response.status_code == 200


def testCharacterAction(client, app):
    response = client.get("/api/worlds", headers={"Authorization": bearer_token(app)})
    wid = response.json[0]["id"]

    response = client.get(
        f"/api/worlds/{wid}/characters", headers={"Authorization": bearer_token(app)}
    )
    cid = response.json[0]["id"]

    response = client.get(
        f"/api/worlds/{wid}/items", headers={"Authorization": bearer_token(app)}
    )
    item_id = response.json[0]["id"]

    response = client.post(
        f"/api/worlds/{wid}/characters/{cid}/action",
        headers={
            "Content-Type": "application/json",
            "Authorization": bearer_token(app),
        },
        json={"item": item_id},
    )
    assert response.status_code == 200
    content = response.json
    # TODO: setup test data for succesful usage
    # assert content["changed"]
    # assert content["event"] is not None
    # assert len(content["event"]) > 0
    # assert content["reply"] is not None
    # assert len(content["reply"]) > 0
    assert content["world_status"]["response_message"] is not None
    assert len(content["world_status"]["response_message"]) > 0
