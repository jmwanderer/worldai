import os
import sqlite3
import unittest

from worldai import chunk, elements, info_set, world_state


class BasicTestCase(unittest.TestCase):

    def setUp(self):
        info_set.TEST = True
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
        self.wstate_id = world_state.getWorldStateID(self.db, session_id, self.world.getID())
        self.wstate = world_state.loadWorldState(self.db, self.wstate_id)

    def tearDown(self):
        self.db.close()

    def testBasics(self):
        doc_id = info_set.InfoStore.addInfoDoc(
            self.db, self.world.getID(), "This is my content"
        )
        info_set.InfoStore.updateInfoDoc(self.db, doc_id, "This is more content")
        info_set.InfoStore.deleteInfoDoc(self.db, doc_id)

    def testOwner(self):
        doc_id = info_set.InfoStore.addInfoDoc(
            self.db,
            self.world.getID(),
            "This is my content",
            owner_id=self.character.getID(),
        )
        info_set.InfoStore.updateInfoDoc(self.db, doc_id, "This is more content")
        info_set.InfoStore.deleteInfoDoc(self.db, doc_id)

    def testWorldState(self):
        doc_id = info_set.InfoStore.addInfoDoc(
            self.db, "This is my content", self.world.getID(), wstate_id=self.wstate_id
        )
        info_set.InfoStore.updateInfoDoc(self.db, doc_id, "This is more content")
        info_set.InfoStore.deleteInfoDoc(self.db, doc_id)

    def testOwnerWorldState(self):
        doc_id = info_set.InfoStore.addInfoDoc(
            self.db,
            "This is my content",
            self.world.getID(),
            owner_id=self.character.getID(),
            wstate_id=self.wstate_id,
        )
        info_set.InfoStore.updateInfoDoc(self.db, doc_id, "This is more content")
        info_set.InfoStore.deleteInfoDoc(self.db, doc_id)

    def testBasicChunk(self):
        doc_id = info_set.InfoStore.addInfoDoc(
            self.db, self.world.getID(), "This is my content"
        )
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
        info_set.InfoStore.addInfoChunk(self.db, doc_id, "chunk content 1")
        info_set.InfoStore.addInfoChunk(self.db, doc_id, "chunk content 2")
        info_set.InfoStore.addInfoChunk(self.db, doc_id, "chunk content 3")

    def testAvailChunks(self):
        owner_id = "1"
        wstate_id = "2"
        # Create 4 docs with different levels of visbility
        doc_id1 = info_set.InfoStore.addInfoDoc(
            self.db, self.world.getID(), "This is my content"
        )

        doc_id2 = info_set.InfoStore.addInfoDoc(
            self.db, self.world.getID(), "This is my content", owner_id=owner_id
        )

        doc_id3 = info_set.InfoStore.addInfoDoc(
            self.db, self.world.getID(), "This is my content", wstate_id=wstate_id
        )

        doc_id4 = info_set.InfoStore.addInfoDoc(
            self.db,
            self.world.getID(),
            "This is my content",
            wstate_id=wstate_id,
            owner_id=owner_id,
        )
        # Add chunks
        self.addChunks(doc_id1)
        self.addChunks(doc_id2)
        self.addChunks(doc_id3)
        self.addChunks(doc_id4)

        # Vectorize
        chunk_id = info_set.InfoStore.getOneNewChunk(self.db)
        while chunk_id is not None:
            content = info_set.InfoStore.getChunkContent(self.db, chunk_id)
            embedding = info_set.generateEmbedding(content)
            info_set.InfoStore.updateChunkEmbed(self.db, chunk_id, embedding)
            chunk_id = info_set.InfoStore.getOneNewChunk(self.db)

        # Add more chunks w/o vectors
        self.addChunks(doc_id1)
        self.addChunks(doc_id2)
        self.addChunks(doc_id3)
        self.addChunks(doc_id4)

        chunk_list = info_set.InfoStore.getAvailableChunks(self.db, self.world.getID())
        self.assertEqual(len(chunk_list), 3)

        chunk_list = info_set.InfoStore.getAvailableChunks(
            self.db, self.world.getID(), owner_id=owner_id
        )
        self.assertEqual(len(chunk_list), 6)

        chunk_list = info_set.InfoStore.getAvailableChunks(
            self.db, self.world.getID(), wstate_id=wstate_id
        )
        self.assertEqual(len(chunk_list), 6)

        chunk_list = info_set.InfoStore.getAvailableChunks(
            self.db, self.world.getID(), wstate_id=wstate_id, owner_id=owner_id
        )
        self.assertEqual(len(chunk_list), 12)

    def testDocument(self):
        path = os.path.join(self.dir_name, "sample.txt")
        with open(path) as f:
            text = f.read()

        doc_id = info_set.addInfoDoc(self.db, self.world.getID(), text)

        info_set.updateInfoDoc(self.db, doc_id, text)

        info_set.deleteInfoDoc(self.db, doc_id)

    def testLookup(self):
        embed = info_set.generateEmbedding("Aria Blackwood")
        path = os.path.join(self.dir_name, "sample.txt")
        with open(path) as f:
            text = f.read()
        info_set.addInfoDoc(self.db, self.world.getID(), text)

        chunks = info_set.getOrderedChunks(self.db, self.world.getID(), embed)
        self.assertEqual(len(chunks), 0)

        while info_set.addEmbeddings(self.db):
            pass

        chunks = info_set.getOrderedChunks(self.db, self.world.getID(), embed)
        self.assertNotEqual(len(chunks), 0)

        for i in range(0, len(chunks) - 2):
            self.assertLessEqual(chunks[i][1], chunks[i + 1][1])

        content = info_set.getInformation(self.db, self.world.getID(), embed, 2)
        self.assertTrue(len(content) > 0)

    def testChunk(self):
        result = chunk.chunk_text(TEXT, 200, 0.2)
        self.assertEqual(len(result), 1)

        result = chunk.chunk_text("\n".join([TEXT, TEXT, TEXT]), 200, 0.2)
        self.assertEqual(len(result), 3)


TEXT = """Jakumbi: A character with a quick wit and great intelligence. He is skilled at hitting a bullseye at 100 yards, demonstrating incredible marksmanship. In addition to his sharpshooting abilities, Jakumbi is also a strong weight lifter and enjoys playing computer games.
Jakumbi is a cunning and intelligent individual, known for his quick wit and sharp mind. His impressive marksmanship, with the ability to hit a bullseye at 100 yards, sets him apart as a skilled sharpshooter. Additionally, his strength as a weight lifter and his passion for computer games add depth to his character."""
