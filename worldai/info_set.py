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

import os


class InfoStore:
  def addInfoDoc(db, content, owner_id = None, wstate_id = None):
    """
    Create a new infoDocEntry
    """
    doc_id = "id%s" % os.urandom(8).hex()
    q = db.execute("INSERT INTO info_docs (id, owner_id, wstate_id, " +
                   " content) VALUES (?, ?, ?, ?)",
                   (doc_id, owner_id, wstate_id, content))
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

  def getAvailableChunks(db, owner_id = None, wstate_id = None):
    if owner_id is not None and wstate_id is not None:
      q = db.execute("SELECT c.id, c.embedding FROM info_chunks as c JOIN " +
                     "info_docs as d ON c.doc_id = d.id " +
                     "WHERE embedding IS NOT NULL AND " +
                     "(d.owner_id IS NULL or d.owner_id = ?) AND " +
                     "(d.wstate_id IS NULL or d.wstate_id = ?)",
                     (owner_id, wstate_id))

    elif owner_id is not None:
      q = db.execute("SELECT c.id, c.embedding FROM info_chunks as c JOIN " +
                     "info_docs as d ON c.doc_id = d.id " +
                     "WHERE embedding IS NOT NULL AND " +
                     "(d.owner_id IS NULL or d.owner_id = ?) AND " +
                     "d.wstate_id IS NULL",
                     (owner_id, ))

    elif wstate_id is not None:
      q = db.execute("SELECT c.id, c.embedding FROM info_chunks as c JOIN " +
                     "info_docs as d ON c.doc_id = d.id " +
                     "WHERE embedding IS NOT NULL AND " +
                     "d.owner_id IS NULL AND " +
                     "(d.wstate_id IS NULL or d.wstate_id = ?)",
                     (wstate_id))
    else:
      q = db.execute("SELECT c.id, c.embedding FROM info_chunks AS c JOIN " +
                     "info_docs AS d ON c.doc_id = d.id " +
                     "WHERE embedding IS NOT NULL AND " +
                     "d.owner_id IS NULL AND " +
                     "d.wstate_id IS NULL")

    return q.fetchall()

  def updateChunkEmbed(db, chunk_id, embedding):
    q = db.execute("UPDATE info_chunks SET embedding = ? WHERE id = ?",
                   (embedding, chunk_id))
    db.commit()
    


    

    
    

    


  
 

  


