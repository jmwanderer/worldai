#!/usr/bin/env python3
"""
ElementInfo: Capture information about elements into the InfoSet

Characters can look up information in the InfoSet

Tables:
- element_info
"""

from . import elements
from . import info_set
import logging

def UpdateElementInfo(db, element: elements.Element):
    """
    Create or update info store for element
    """
    logging.info("update element info %s", element.getName())
    world_id = element.parent_id
    if element.type == elements.ElementType.WORLD:
        world_id = element.id

    content = element.getName()
    if element.getDescription() is not None:
        content = content + ": " + element.getDescription()
    if element.getDetails() is not None:
        content = content + "\n" + element.getDetails()
             
    c = db.cursor()
    c.execute("SELECT doc_id FROM element_info WHERE element_id = ?",
              (element.getID(),))
    r = c.fetchone()
    if r is None:
        doc_id = info_set.addInfoDoc(db, world_id, content)
        c.execute("INSERT INTO element_info (element_id, doc_id) VALUES (?,?)",
                  (element.getID(), doc_id))
        db.commit()
    else:
        doc_id = r[0]
        info_set.updateInfoDoc(db, doc_id, content)


def DeleteElementInfo(db, element_id):
    """
    Remove Element info for the given element.
    """
    c = db.cursor()
    c.execute("SELECT doc_id FROM element_info WHERE element_id = ?",
              (element_id,))
    r = c.fetchone()
    if r is not None:
        doc_id = r[0]
        c.execute("DELETE FROM element_info WHERE element_id = ?",
                  (element_id,))
        db.commit()
        info_set.deleteInfoDoc(db, doc_id)


    pass
