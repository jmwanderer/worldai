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
from . import chunk

import os
import random
import json
import openai

TEST=False

class InfoStore:
  def addInfoDoc(db, world_id, content, owner_id = None, wstate_id = None):
    """
    Create a new infoDocEntry
    """
    doc_id = "id%s" % os.urandom(8).hex()
    print(f"Add info doc world id = {world_id}")
    q = db.execute("INSERT INTO info_docs (id, world_id, owner_id, " +
                   "wstate_id, content) VALUES (?, ?, ?, ?, ?)",
                   (doc_id, world_id, owner_id, wstate_id, content))
    db.commit()
    return doc_id


  def updateInfoDoc(db, doc_id, content):
    q = db.execute("UPDATE info_docs SET content = ? WHERE id = ?",
                   (content, doc_id))
    db.commit()

  def deleteInfoDoc(db, doc_id):
    q = db.execute("DELETE FROM info_docs WHERE id = ?",
                   (doc_id,))
    db.commit()

  def addInfoChunk(db, doc_id, content):
    """
    Create a new chunk entry
    """
    chunk_id = "id%s" % os.urandom(8).hex()    
    q = db.execute("INSERT INTO info_chunks (id, doc_id, content) " +
                   "VALUES (?, ?, ?)",
                   (chunk_id, doc_id, content))
    db.commit()
    return chunk_id

  def getChunkContent(db, chunk_id):
    q = db.execute("SELECT content FROM info_chunks WHERE id = ?",
                   (chunk_id,))
    r = q.fetchone()
    if r is None:
      return None
    return r[0]

  def deleteDocChunks(db, doc_id):
    q = db.execute("DELETE FROM info_chunks WHERE doc_id = ?",
                   (doc_id,))
    db.commit()

  def getOneNewChunk(db):
    q = db.execute("SELECT id FROM info_chunks WHERE embedding IS NULL")
    r = q.fetchone()
    if r is None:
      return None
    return r[0]

  def getAvailableChunks(db, world_id, owner_id = None, wstate_id = None):
    if owner_id is not None and wstate_id is not None:
      q = db.execute("SELECT c.id, c.embedding FROM info_chunks as c JOIN " +
                     "info_docs as d ON c.doc_id = d.id " +
                     "WHERE embedding IS NOT NULL AND " +
                     "world_id = ? AND " +
                     "(d.owner_id IS NULL or d.owner_id = ?) AND " +
                     "(d.wstate_id IS NULL or d.wstate_id = ?)",
                     (world_id, owner_id, wstate_id))

    elif owner_id is not None:
      q = db.execute("SELECT c.id, c.embedding FROM info_chunks as c JOIN " +
                     "info_docs as d ON c.doc_id = d.id " +
                     "WHERE embedding IS NOT NULL AND " +
                     "world_id = ? AND " +                     
                     "(d.owner_id IS NULL or d.owner_id = ?) AND " +
                     "d.wstate_id IS NULL",
                     (world_id, owner_id, ))

    elif wstate_id is not None:
      q = db.execute("SELECT c.id, c.embedding FROM info_chunks as c JOIN " +
                     "info_docs as d ON c.doc_id = d.id " +
                     "WHERE embedding IS NOT NULL AND " +
                     "world_id = ? AND " +
                     "d.owner_id IS NULL AND " +
                     "(d.wstate_id IS NULL or d.wstate_id = ?)",
                     (world_id, wstate_id))
    else:
      q = db.execute("SELECT c.id, c.embedding FROM info_chunks AS c JOIN " +
                     "info_docs AS d ON c.doc_id = d.id " +
                     "WHERE embedding IS NOT NULL AND " +
                     "world_id = ? AND " +
                     "d.owner_id IS NULL AND " +
                     "d.wstate_id IS NULL",
                     (world_id,))

    result = []
    for (chunk_id, str_val) in q.fetchall():
      embed = json.loads(str_val)
      result.append((chunk_id, embed))
    return result

  def updateChunkEmbed(db, chunk_id, embedding):
    str_val = json.dumps(embedding)
    q = db.execute("UPDATE info_chunks SET embedding = ? WHERE id = ?",
                   (str_val, chunk_id))
    db.commit()


def _compute_distance(v1, v2):
  """
  Return the square of distance between the vectors
  To get consistent distance, take the sqrt.
  """
  #TODO: look at https://platform.openai.com/docs/guides/embeddings/use-cases
  total = 0
  index = 0
  while (index < len(v1) and index < len(v2)):
    v = (v1[index] - v2[index])
    index += 1
    total += v*v
  return total


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

  response = _get_aiclient().embeddings.create(input = content,
                                               model = "text-embedding-ada-002")
  return response.data[0].embedding


def addInfoDoc(db, world_id, content, owner_id = None, wstate_id = None):
  doc_id = InfoStore.addInfoDoc(db, world_id, content, owner_id, wstate_id)
  result = chunk.chunk_text(content, 100, .3)
  for entry in result:
    InfoStore.addInfoChunk(db, doc_id, entry)
  return doc_id

def updateInfoDoc(db, doc_id, content):
  InfoStore.updateInfoDoc(db, doc_id, content)
  InfoStore.deleteDocChunks(db, doc_id)
  result = chunk.chunk_text(content, 100, .3)
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

def getOrderedChunks(db, world_id, embed, owner_id = None, wstate_id = None):

  chunks = InfoStore.getAvailableChunks(db, world_id,
                                        owner_id = owner_id,
                                        wstate_id = wstate_id)
  result = []
  for entry in chunks:
    result.append((entry[0], _compute_distance(embed, entry[1])))
  result.sort(key = lambda a : a[1])

  return result

def getInformation(db, world_id, embed, count):
  results = ""
  entries = getOrderedChunks(db, world_id, embed)
  for i in range(0, min(count, len(entries))):
    content = InfoStore.getChunkContent(db, entries[i][0])
    results = results + content
  return content
                 
    
    

