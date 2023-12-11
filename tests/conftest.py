import pytest
import os
import tempfile
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

  yield app

  instance_path.cleanup()

  
@pytest.fixture()
def client(app):
  return app.test_client()


@pytest.fixture()
def runner(app):
  return app.text_cli_runner()

