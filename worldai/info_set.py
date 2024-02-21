#!/usr/bin/env python3
"""
InfoSet: Document storage into vector database

Planned uses:
- World history and facts that anyone can access
- Character specific knowledge that only character can access
- Character chat history, only character instance can access

Tables:
- info_docs
- info_chunks
"""
import json
import logging
import os
import random

import numpy as np
import openai

from . import chunk

TEST = False


class InfoStore:
    @staticmethod
    def addInfoDoc(db, world_id, content, owner_id=None, wstate_id=None):
        """
        Create a new infoDocEntry
        """
        doc_id = "id%s" % os.urandom(8).hex()
        db.execute(
            "INSERT INTO info_docs (id, world_id, owner_id, "
            + "wstate_id, content) VALUES (?, ?, ?, ?, ?)",
            (doc_id, world_id, owner_id, wstate_id, content),
        )
        db.commit()
        return doc_id

    @staticmethod
    def updateInfoDoc(db, doc_id, content):
        db.execute(
            "UPDATE info_docs SET content = ? WHERE id = ?", (content, doc_id)
        )
        db.commit()

    @staticmethod        
    def deleteInfoDoc(db, doc_id):
        db.execute("DELETE FROM info_docs WHERE id = ?", (doc_id,))
        db.commit()

    @staticmethod        
    def addInfoChunk(db, doc_id, content):
        """
        Create a new chunk entry
        """
        chunk_id = "id%s" % os.urandom(8).hex()
        db.execute(
            "INSERT INTO info_chunks (id, doc_id, content) " + "VALUES (?, ?, ?)",
            (chunk_id, doc_id, content),
        )
        db.commit()
        return chunk_id

    @staticmethod    
    def getChunkContent(db, chunk_id):
        q = db.execute("SELECT content FROM info_chunks WHERE id = ?", (chunk_id,))
        r = q.fetchone()
        if r is None:
            return None
        return r[0]

    @staticmethod    
    def deleteDocChunks(db, doc_id):
        db.execute("DELETE FROM info_chunks WHERE doc_id = ?", (doc_id,))
        db.commit()

    @staticmethod        
    def getOneNewChunk(db):
        q = db.execute("SELECT id FROM info_chunks WHERE embedding IS NULL")
        r = q.fetchone()
        if r is None:
            return None
        return r[0]

    @staticmethod    
    def getAvailableChunks(db, world_id, owner_id=None, wstate_id=None):
        if owner_id is not None and wstate_id is not None:
            q = db.execute(
                "SELECT c.id, c.embedding FROM info_chunks as c JOIN "
                + "info_docs as d ON c.doc_id = d.id "
                + "WHERE embedding IS NOT NULL AND "
                + "world_id = ? AND "
                + "(d.owner_id IS NULL or d.owner_id = ?) AND "
                + "(d.wstate_id IS NULL or d.wstate_id = ?)",
                (world_id, owner_id, wstate_id),
            )

        elif owner_id is not None:
            q = db.execute(
                "SELECT c.id, c.embedding FROM info_chunks as c JOIN "
                + "info_docs as d ON c.doc_id = d.id "
                + "WHERE embedding IS NOT NULL AND "
                + "world_id = ? AND "
                + "(d.owner_id IS NULL or d.owner_id = ?) AND "
                + "d.wstate_id IS NULL",
                (
                    world_id,
                    owner_id,
                ),
            )

        elif wstate_id is not None:
            q = db.execute(
                "SELECT c.id, c.embedding FROM info_chunks as c JOIN "
                + "info_docs as d ON c.doc_id = d.id "
                + "WHERE embedding IS NOT NULL AND "
                + "world_id = ? AND "
                + "d.owner_id IS NULL AND "
                + "(d.wstate_id IS NULL or d.wstate_id = ?)",
                (world_id, wstate_id),
            )
        else:
            q = db.execute(
                "SELECT c.id, c.embedding FROM info_chunks AS c JOIN "
                + "info_docs AS d ON c.doc_id = d.id "
                + "WHERE embedding IS NOT NULL AND "
                + "world_id = ? AND "
                + "d.owner_id IS NULL AND "
                + "d.wstate_id IS NULL",
                (world_id,),
            )

        result = []
        for chunk_id, str_val in q.fetchall():
            embed = json.loads(str_val)
            result.append((chunk_id, embed))
        return result

    @staticmethod    
    def updateChunkEmbed(db, chunk_id, embedding):
        str_val = json.dumps(embedding)
        db.execute(
            "UPDATE info_chunks SET embedding = ? WHERE id = ?", (str_val, chunk_id)
        )
        db.commit()



client = None

def _get_aiclient():
    global client
    if client is None:
        client = openai.OpenAI(api_key=openai.api_key)
    return client


def generateEmbedding(content):
    if TEST:
        result = []
        for c in range(1, 100):
            result.append(round(random.uniform(0, 1), 8))
            return result

    response = _get_aiclient().embeddings.create(
        input=content, model="text-embedding-3-small"
    )
    return response.data[0].embedding


def addInfoDoc(db, world_id, content, owner_id=None, wstate_id=None):
    # TODO: add a no chunk option
    doc_id = InfoStore.addInfoDoc(db, world_id, content, owner_id, wstate_id)
    logging.info("Add info doc id:%s, world id: %s", doc_id, world_id)
    result = chunk.chunk_text(content, 200, 0.2)
    for entry in result:
        InfoStore.addInfoChunk(db, doc_id, entry)
    return doc_id


def updateInfoDoc(db, doc_id, content):
    logging.info("Update info doc id:%s ", doc_id)
    # TODO: consider checking if the document changed.
    InfoStore.updateInfoDoc(db, doc_id, content)
    InfoStore.deleteDocChunks(db, doc_id)
    result = chunk.chunk_text(content, 200, 0.2)
    for entry in result:
        InfoStore.addInfoChunk(db, doc_id, entry)


def deleteInfoDoc(db, doc_id):
    InfoStore.deleteDocChunks(db, doc_id)
    InfoStore.deleteInfoDoc(db, doc_id)


def addEmbeddings(db):
    chunk_id = InfoStore.getOneNewChunk(db)
    if chunk_id is not None:
        content = InfoStore.getChunkContent(db, chunk_id)
        embed = generateEmbedding(content)
        InfoStore.updateChunkEmbed(db, chunk_id, embed)
        return True
    return False


def getChunkContent(db, chunk_id):
    return InfoStore.getChunkContent(db, chunk_id)


def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def getOrderedChunks(db, world_id, embed, owner_id=None, wstate_id=None):

    chunks = InfoStore.getAvailableChunks(
        db, world_id, owner_id=owner_id, wstate_id=wstate_id
    )
    result = []
    for entry in chunks:
        result.append((entry[0], cosine_similarity(embed, entry[1])))
    result.sort(key=lambda a: a[1], reverse=True)

    return result

def getInformation(db, world_id, embed, count):
    results = []
    entries = getOrderedChunks(db, world_id, embed)
    for i in range(0, min(count, len(entries))):
        content = InfoStore.getChunkContent(db, entries[i][0])
        logging.info("%d: info lookup: %s", i, content)
        results.append(content)
    return "\n".join(results)
