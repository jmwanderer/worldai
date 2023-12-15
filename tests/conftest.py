import pytest
import os
import tempfile
import worldai.db_access
import worldai.server

"""
Test fixtures for WorldAI
- application
- web client
- CLI client
"""

@pytest.fixture()
def app():
  instance_path = tempfile.TemporaryDirectory()  
  
  app = worldai.server.create_app(instance_path=instance_path.name)
  app.config.update({
    "TESTING": True,
    })

  # Populate with test data
  path = os.path.join(os.path.dirname(__file__), "test_data.sql")
  db = worldai.db_access.open_db()
  with open(path) as f:
    db.executescript(f.read())
  db.close()

  yield app

  instance_path.cleanup()

  
@pytest.fixture()
def client(app):
  return app.test_client()


@pytest.fixture()
def runner(app):
  return app.text_cli_runner()

