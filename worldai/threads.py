"""
Chat history for each character

(nothing to do with OS threads)

    Jim Wanderer
    http://github.com/jmwanderer
"""


import os
import time

#
# Module to manage thread information in the database
#


def get_thread(db, session_id):
    c = db.execute("SELECT thread FROM threads WHERE id = ? ", (session_id,))
    r = c.fetchone()
    if r is not None:
        thread = r[0]
        return thread
    return None


def save_thread(db, session_id, thread):
    now = time.time()
    c = db.cursor()
    c.execute("BEGIN EXCLUSIVE")
    c.execute("SELECT count(*) FROM threads WHERE id = ? ", (session_id,))
    if c.fetchone()[0] == 0:
        # INSERT
        c.execute(
            "INSERT INTO threads VALUES (?, ?, ?, ?)", (session_id, now, now, thread)
        )
    else:
        # UPDATE
        c.execute(
            "UPDATE threads SET thread = ?, updated = ? WHERE id = ?",
            (thread, now, session_id),
        )
    c.execute("commit")


def delete_thread(db, session_id):
    db.execute("DELETE FROM threads WHERE id = ?", (session_id,))
    db.commit()


def get_character_thread(db, world_state_id, cid):
    """
    Return a session thread for a specific character.
    None if it does not yet exist.
    """
    c = db.execute(
        "SELECT threads.thread FROM threads "
        + "JOIN character_threads ON "
        + "character_threads.thread_id = threads.id "
        + "WHERE character_threads.world_state_id = ? AND "
        + "character_threads.character_id = ?",
        (world_state_id, cid),
    )
    r = c.fetchone()
    if r is not None:
        thread = r[0]
        return thread
    return None


def save_character_thread(db, world_state_id, cid, thread):
    """
    Updated a session thread for a specific character.
    Create if needed.
    """
    now = time.time()
    c = db.cursor()
    c.execute("BEGIN EXCLUSIVE")
    c.execute(
        "SELECT thread_id FROM character_threads WHERE "
        + "world_state_id = ? AND character_id = ?",
        (world_state_id, cid),
    )
    r = c.fetchone()
    if r is not None:
        thread_id = r[0]
        # UPDATE
        c.execute(
            "UPDATE threads SET thread = ?, updated = ? WHERE id = ?",
            (thread, now, thread_id),
        )
    else:
        # INSERT
        thread_id = os.urandom(12).hex()
        c.execute(
            "INSERT INTO threads VALUES (?, ?, ?, ?)", (thread_id, now, now, thread)
        )
        c.execute(
            "INSERT INTO character_threads (world_state_id, character_id, "
            + "thread_id) VALUES (?, ?, ?)",
            (world_state_id, cid, thread_id),
        )
    db.commit()


def delete_character_thread(db, world_state_id, cid):
    c = db.cursor()
    c.execute("BEGIN EXCLUSIVE")
    c.execute(
        "SELECT thread_id FROM character_threads WHERE "
        + "world_state_id = ? AND character_id = ?",
        (world_state_id, cid),
    )

    r = c.fetchone()
    if r is not None:
        thread_id = r[0]
        c.execute(
            "DELETE FROM character_threads WHERE "
            + "world_state_id = ? AND character_id = ?",
            (world_state_id, cid),
        )
        c.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
    db.commit()
