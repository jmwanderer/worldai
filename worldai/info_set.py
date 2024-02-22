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
import typing

from . import chunk, elements

import pydantic


# Types for IDs
DocID = typing.NewType('DocID', str)
ChunkID = typing.NewType('ChunkID', str)

TEST = False


class InfoStore:
    @staticmethod
    def addInfoDoc(db, 
                   world_id: elements.WorldID, 
                   content: str, 
                   owner_id: elements.ElemID | None = None,
                   wstate_id: str|None = None) -> DocID:
        doc_id: DocID = DocID("id%s" % os.urandom(8).hex())
        # Put a Null into the DB instead of """
        db.execute(
            "INSERT INTO info_docs (id, world_id, owner_id, "
            + "wstate_id, content) VALUES (?, ?, ?, ?, ?)",
            (doc_id, world_id, owner_id, wstate_id, content),
        )
        db.commit()
        return doc_id

    @staticmethod
    def updateInfoDoc(db, doc_id: DocID, content: str) -> None:
        db.execute(
            "UPDATE info_docs SET content = ? WHERE id = ?", (content, doc_id)
        )
        db.commit()

    @staticmethod
    def getInfoDoc(db, doc_id: DocID) -> str:
        """
        Return the content of the specified info doc entry
        """
        q = db.execute("SELECT content FROM info_docs WHERE id = ?", (doc_id,))
        r = q.fetchone()
        if r is not None:
            return r[0]
        return ""

    @staticmethod        
    def deleteInfoDoc(db, doc_id: DocID) -> None:
        db.execute("DELETE FROM info_docs WHERE id = ?", (doc_id,))
        db.commit()

    @staticmethod        
    def addInfoChunk(db, doc_id: DocID, content: str, embedding: list[float]|None =None) -> ChunkID:
        """
        Create a new chunk entry
        """
        chunk_id: ChunkID = ChunkID("id%s" % os.urandom(8).hex())
        if embedding is None:
            str_val = None
        else:
            str_val = json.dumps(embedding)

        db.execute(
            "INSERT INTO info_chunks (id, doc_id, content, embedding) " + "VALUES (?, ?, ?,?)",
            (chunk_id, doc_id, content, str_val),
        )
        db.commit()
        return chunk_id

    @staticmethod    
    def getChunkContent(db, chunk_id: ChunkID) -> str:
        q = db.execute("SELECT content FROM info_chunks WHERE id = ?", (chunk_id,))
        r = q.fetchone()
        if r is None:
            return ""
        return r[0]

    @staticmethod    
    def deleteDocChunks(db, doc_id: DocID):
        db.execute("DELETE FROM info_chunks WHERE doc_id = ?", (doc_id,))
        db.commit()

    @staticmethod        
    def getOneNewChunk(db) -> ChunkID|None:
        q = db.execute("SELECT id FROM info_chunks WHERE embedding IS NULL")
        r = q.fetchone()
        if r is None:
            return None
        return ChunkID(r[0])

    @staticmethod    
    def getAvailableChunks(db, 
                           world_id: elements.WorldID,
                           owner_id: elements.ElemID|None = None,
                           wstate_id: str|None = None) -> list[tuple[ChunkID, list[float]]]:
        if owner_id is not None and wstate_id is not None:
            # Lookup state entry with an owner in a specific world
            # This is a character thread
            q = db.execute(
                "SELECT c.id, c.embedding FROM info_chunks as c JOIN "
                + "info_docs as d ON c.doc_id = d.id "
                + "WHERE embedding IS NOT NULL AND "
                + "world_id = ? AND "
                + "d.owner_id = ? AND "
                + "d.wstate_id = ?",
                (world_id, owner_id, wstate_id),
            )

        elif owner_id is not None:
            # Lookup a private doc for an owner
            q = db.execute(
                "SELECT c.id, c.embedding FROM info_chunks as c JOIN "
                + "info_docs as d ON c.doc_id = d.id "
                + "WHERE embedding IS NOT NULL AND "
                + "world_id = ? AND "
                + "d.owner_id = ? AND "
                + "d.wstate_id IS NULL",
                (
                    world_id,
                    owner_id,
                ),
            )

        elif wstate_id is not None:
            # Lookup public docs specific to a world instance
            # or public docs for a world.
            # Not currently used - may change depending on need
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
            # Lookup public world doc
            q = db.execute(
                "SELECT c.id, c.embedding FROM info_chunks AS c JOIN "
                + "info_docs AS d ON c.doc_id = d.id "
                + "WHERE embedding IS NOT NULL AND "
                + "world_id = ? AND "
                + "d.owner_id IS NULL AND "
                + "d.wstate_id IS NULL",
                (world_id,),
            )

        result: list[tuple[ChunkID, list[float]]] = []
        for chunk_id, str_val in q.fetchall():
            embed = json.loads(str_val)
            result.append((chunk_id, embed))
        return result

    @staticmethod    
    def updateChunkEmbed(db, chunk_id: ChunkID, embedding:list[float]):
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


def generateEmbedding(content: str) -> list[float]:
    if TEST:
        result = []
        for c in range(1, 100):
            result.append(round(random.uniform(0, 1), 8))
            return result

    response = _get_aiclient().embeddings.create(
        input=content, model="text-embedding-3-small"
    )
    return response.data[0].embedding

def addInfoDoc(db, world_id: elements.WorldID, 
               content: str, 
               owner_id: elements.ElemID|None = None, 
               wstate_id: str|None = None) -> DocID:
    doc_id = InfoStore.addInfoDoc(db, world_id, content, owner_id, wstate_id)
    logging.info("Add info doc id:%s, world id: %s", doc_id, world_id)
    result = chunk.chunk_text(content, 200, 0.2)
    for entry in result:
        InfoStore.addInfoChunk(db, doc_id, entry)
    return doc_id


def updateInfoDoc(db, doc_id: DocID, content: str) -> None:
    logging.info("Update info doc id:%s ", doc_id)
    # TODO: consider checking if the document changed.
    InfoStore.updateInfoDoc(db, doc_id, content)
    InfoStore.deleteDocChunks(db, doc_id)
    result = chunk.chunk_text(content, 200, 0.2)
    for entry in result:
        InfoStore.addInfoChunk(db, doc_id, entry)


def addInfoNote(db, world_id: elements.WorldID, 
                content: str, 
                owner_id: elements.ElemID|None = None,
                wstate_id: str|None = None) -> DocID:
    """
    Add a short entry that isn't chunked and will get an embedding immediately.
    """
    # Entry that isn't chunked and has an embedding generated immediately
    doc_id = InfoStore.addInfoDoc(db, world_id, content, owner_id, wstate_id)
    logging.info("Add info note id:%s, world id: %s", doc_id, world_id)
    embed = generateEmbedding(content)
    InfoStore.addInfoChunk(db, doc_id, content, embed)
    return doc_id

def updateInfoNote(db, doc_id: DocID, content: str) -> bool:
    """
    Update the short entry, return False if it exceeds the size boundary
    """
    logging.info("Update info  id:%s len(%d)", doc_id, len(content))
    # Arbitrary limit in characters.
    if len(content) > 1200:
        return False
    InfoStore.updateInfoDoc(db, doc_id, content)
    InfoStore.deleteDocChunks(db, doc_id)
    embed = generateEmbedding(content)
    InfoStore.addInfoChunk(db, doc_id, content, embed)
    return True

def getInfoDoc(db, doc_id: DocID) -> str:
    return InfoStore.getInfoDoc(db, doc_id)

def deleteInfoDoc(db, doc_id: DocID):
    InfoStore.deleteDocChunks(db, doc_id)
    InfoStore.deleteInfoDoc(db, doc_id)


def addEmbeddings(db) -> bool:
    chunk_id = InfoStore.getOneNewChunk(db)
    if chunk_id is not None:
        content = InfoStore.getChunkContent(db, chunk_id)
        embed = generateEmbedding(content)
        InfoStore.updateChunkEmbed(db, chunk_id, embed)
        return True
    return False


def getChunkContent(db, chunk_id: ChunkID) -> str:
    return InfoStore.getChunkContent(db, chunk_id)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def getOrderedChunks(db, world_id: elements.WorldID, 
                     embed: list[float], 
                     owner_id: elements.ElemID|None = None, 
                     wstate_id: str|None = None) -> list[tuple[ChunkID, float]]:

    chunks = InfoStore.getAvailableChunks(
        db, world_id, owner_id=owner_id, wstate_id=wstate_id
    )
    result = []
    for entry in chunks:
        result.append((entry[0], cosine_similarity(embed, entry[1])))
    result.sort(key=lambda a: a[1], reverse=True)

    return result

def getInformation(db, world_id: elements.WorldID, 
                   embed: list[float], count: int) -> str:
    """
    Return count number of entries that are closet to the  given embedding
    Result is a concat of strings for all included entries
    """
    results = []
    entries = getOrderedChunks(db, world_id, embed)
    for i in range(0, min(count, len(entries))):
        content = InfoStore.getChunkContent(db, entries[i][0])
        logging.info("%d: info lookup: %s", i, content)
        results.append(content)
    return "\n".join(results)
