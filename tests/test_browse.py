"""
Test the basics in the HTML interface.
- Assumed a popualted database with specific IDs.
"""


def do_login(client, app):
    """
    Post auth  key to the login page.
    Will get a session cookie that enables access.
    """
    response = client.post(
        "/login",
        data={
            "auth_key": app.config["AUTH_KEY"],
        },
    )
    assert response.status_code == 302
    assert response.location == "/"


def test_no_login(client):
    # No login
    response = client.get("/")
    assert response.status_code == 302
    assert response.location.startswith("/login")


def test_login(client, app):
    do_login(client, app)
    response = client.get("/")
    assert response.status_code == 200
    assert b"<h2>" in response.data


def test_play_no_login(client, app):
    response = client.get("/ui/play")
    assert response.status_code == 302


def test_design_login(client, app):
    do_login(client, app)
    response = client.get("/ui/design")
    assert response.status_code == 200


def test_play_login(client, app):
    do_login(client, app)
    response = client.get("/ui/play")
    assert response.status_code == 200


def test_view_worlds(client, app):
    do_login(client, app)
    response = client.get("/view/worlds")
    assert response.status_code == 200
    assert b"<h1>" in response.data
    assert b"<h2>" in response.data


def test_view_world_no_exist(client, app):
    do_login(client, app)
    response = client.get("/view/worlds/123")
    assert response.status_code == 404
    assert b"World not found" in response.data


def test_view_world_exist(client, app):
    do_login(client, app)
    response = client.get("/view/worlds/ida00fd73d")
    assert response.status_code == 200
    assert b"Kanazawa World" in response.data


def test_view_character_no_exist(client, app):
    do_login(client, app)
    response = client.get("/view/worlds/123/characters/456")
    assert response.status_code == 404
    assert b"World not found" in response.data

    response = client.get("/view/worlds/ida00fd73d/characters/456")
    assert response.status_code == 404
    assert b"Character not found" in response.data


def test_view_character_exist(client, app):
    do_login(client, app)
    response = client.get("/view/worlds/ida00fd73d/characters/id96c9f2eb")
    assert response.status_code == 200
    assert b"Hiroshi" in response.data


def test_view_items_no_exist(client, app):
    do_login(client, app)
    response = client.get("/view/worlds/123/items/456")
    assert response.status_code == 404
    assert b"World not found" in response.data
    response = client.get("/view/worlds/ida1ad7f2c/items/456")
    assert response.status_code == 404
    assert b"Item not found" in response.data


def test_view_items_exist(client, app):
    do_login(client, app)
    response = client.get("/view/worlds/ida1ad7f2c/items/id5936b090")
    assert response.status_code == 200
    assert b"Silver Sword" in response.data


def test_view_site_no_exit(client, app):
    do_login(client, app)
    response = client.get("/view/worlds/123/sites/456")
    assert response.status_code == 404
    assert b"World not found" in response.data
    response = client.get("/view/worlds/ida1ad7f2c/sites/456")
    assert response.status_code == 404
    assert b"Site not found" in response.data


def test_view_site_exist(client, app):
    do_login(client, app)
    response = client.get("/view/worlds/ida1ad7f2c/sites/id6c7f129d")
    assert response.status_code == 200
    assert b"Kaer Morhen" in response.data
