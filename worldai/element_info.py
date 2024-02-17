#!/usr/bin/env python3
"""
ElementInfo: Capture information about elements into the InfoSet

Characters can look up information in the InfoSet

Tables:
- element_info
"""

import logging

from . import elements, info_set


def UpdateElementInfo(db, element: elements.Element):
    """
    Create or update info store for element
    """
    logging.info("update element info %s", element.getName())
    world_id = element.parent_id
    if element.type == elements.ElementType.WORLD:
        world_id = elements.WorldID(element.getID())

    for index, content in element.getInfoText():
        c = db.cursor()
        c.execute(
            "SELECT doc_id FROM element_info WHERE element_id = ? and info_index = ?",
            (element.getID(), index),
        )
        r = c.fetchone()
        if r is None:
            doc_id = info_set.addInfoDoc(db, world_id, content)
            c.execute(
                "INSERT INTO element_info (element_id, info_index, doc_id) VALUES (?,?,?)",
                (element.getID(), index, doc_id),
            )
            db.commit()
        else:
            doc_id = r[0]
            info_set.updateInfoDoc(db, doc_id, content)


def DeleteElementInfo(db, element_id):
    """
    Remove Element info for the given element.
    """
    c = db.cursor()
    c.execute("SELECT doc_id FROM element_info WHERE element_id = ?", (element_id,))
    for r in c.fetchall():
        doc_id = r[0]

        info_set.deleteInfoDoc(db, doc_id)
    c.execute("DELETE FROM element_info WHERE element_id = ?", (element_id,))
    db.commit()
