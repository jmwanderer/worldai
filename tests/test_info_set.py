from worldai import info_set
from worldai import elements
from worldai import world_state
import unittest
import os
import sqlite3


class BasicTestCase(unittest.TestCase):

  def setUp(self):
    self.dir_name = os.path.dirname(__file__)
    path = os.path.join(self.dir_name, "../worldai/schema.sql")
    self.db = sqlite3.connect("file::memory:")
    with open(path) as f:
      self.db.executescript(f.read())
    world = elements.World()
    world.setName("world")
    self.world = elements.createWorld(self.db, world)
    character = elements.Character(world.getID())
    character.setName("character")
    session_id = "id1234"
    self.character = elements.createCharacter(self.db, character)
    self.wstate_id = world_state.getWorldStateID(self.db,
                                                 session_id,
                                                 self.world.id)
    self.wstate = world_state.loadWorldState(self.db, self.wstate_id)

    
  def tearDown(self):
    self.db.close()

  def testBasics(self):
    doc_id = info_set.InfoStore.addInfoDoc(self.db, "This is my content")
    info_set.InfoStore.updateInfoDoc(self.db, doc_id, "This is more content")
    info_set.InfoStore.deleteInfoDoc(self.db, doc_id)

  def testOwner(self):
    doc_id = info_set.InfoStore.addInfoDoc(self.db, "This is my content",
                                           owner_id = self.character.getID())
    info_set.InfoStore.updateInfoDoc(self.db, doc_id, "This is more content")
    info_set.InfoStore.deleteInfoDoc(self.db, doc_id)
    

  def testWorldState(self):
    doc_id = info_set.InfoStore.addInfoDoc(self.db, "This is my content",
                                           wstate_id = self.wstate_id)
    info_set.InfoStore.updateInfoDoc(self.db, doc_id, "This is more content")
    info_set.InfoStore.deleteInfoDoc(self.db, doc_id)

  def testOwnerWorldState(self):
    doc_id = info_set.InfoStore.addInfoDoc(self.db, "This is my content",
                                           owner_id = self.character.getID(),
                                           wstate_id = self.wstate_id)
    info_set.InfoStore.updateInfoDoc(self.db, doc_id, "This is more content")
    info_set.InfoStore.deleteInfoDoc(self.db, doc_id)
    
  def testBasicChunk(self):
    doc_id = info_set.InfoStore.addInfoDoc(self.db, "This is my content")
    chunk_id = info_set.InfoStore.addInfoChunk(self.db, doc_id, "chunk content")
    content = info_set.InfoStore.getChunkContent(self.db, chunk_id)
    self.assertEqual(content, "chunk content")
    info_set.InfoStore.addInfoChunk(self.db, doc_id, "more chunk content")

    chunk_id = info_set.InfoStore.getOneNewChunk(self.db)
    self.assertIsNotNone(chunk_id)

    info_set.InfoStore.deleteDocChunks(self.db, doc_id)
    chunk_id = info_set.InfoStore.getOneNewChunk(self.db)
    self.assertIsNone(chunk_id)

  def addChunks(self, doc_id):
    info_set.InfoStore.addInfoChunk(self.db, doc_id,
                                    "chunk content 1")
    info_set.InfoStore.addInfoChunk(self.db, doc_id,
                                    "chunk content 2")
    info_set.InfoStore.addInfoChunk(self.db, doc_id,
                                    "chunk content 3")
    
  def testAvailChunks(self):
    owner_id = "1"
    wstate_id = "2"
    # Create 4 docs with different levels of visbility
    doc_id1 = info_set.InfoStore.addInfoDoc(self.db,
                                            "This is my content")

    
    doc_id2 = info_set.InfoStore.addInfoDoc(self.db,
                                            "This is my content",
                                            owner_id = owner_id)

    
    doc_id3 = info_set.InfoStore.addInfoDoc(self.db,
                                            "This is my content",
                                            wstate_id = wstate_id)

    doc_id4 = info_set.InfoStore.addInfoDoc(self.db,
                                            "This is my content",
                                            wstate_id = wstate_id,
                                            owner_id = owner_id)
    # Add chunks
    self.addChunks(doc_id1)
    self.addChunks(doc_id2)
    self.addChunks(doc_id3)
    self.addChunks(doc_id4)    

    # Vectorize
    chunk_id = info_set.InfoStore.getOneNewChunk(self.db)    
    while chunk_id is not None:
      info_set.InfoStore.updateChunkEmbed(self.db, chunk_id, "embedding")
      chunk_id = info_set.InfoStore.getOneNewChunk(self.db)

    # Add more chunks w/o vectors
    self.addChunks(doc_id1)
    self.addChunks(doc_id2)
    self.addChunks(doc_id3)
    self.addChunks(doc_id4)

    chunk_list = info_set.InfoStore.getAvailableChunks(self.db)
    self.assertEqual(len(chunk_list), 3)

    chunk_list = info_set.InfoStore.getAvailableChunks(self.db,
                                                       owner_id = owner_id)
    self.assertEqual(len(chunk_list), 6)

    chunk_list = info_set.InfoStore.getAvailableChunks(self.db,
                                                       wstate_id = wstate_id)
    self.assertEqual(len(chunk_list), 6)

    chunk_list = info_set.InfoStore.getAvailableChunks(self.db,
                                                       wstate_id = wstate_id,
                                                       owner_id = owner_id)
    self.assertEqual(len(chunk_list), 12)
    
