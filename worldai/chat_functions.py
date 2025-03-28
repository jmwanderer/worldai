"""
Base class for Character and Design Functions

    Jim Wanderer
    http://github.com/jmwanderer
"""


import logging


class BaseChatFunctions:
    """
    Base interface used by ChatSession to customize capabilities.

    """

    def __init__(self):
        self.modified = False

    def getProperties(self):
        return {"modified": self.modified}

    def setProperties(self, properties):
        self.modified = properties["modified"]

    def madeChanges(self):
        return self.modified

    def clearChanges(self):
        self.modified = False

    def get_instructions(self, db):
        return ""

    def get_available_tools(self):
        return None

    def track_tokens(self, db, prompt, complete, total):
        world_id = 0
        track_tokens(db, world_id, prompt, complete, total)

    def archive_content(self, db, contents: dict[str, str]) -> None:
        """
        Function to archive a message from a thread
        """
        logging.info("archive content: user=%s", contents["user"])

    def lookup_content(self, db, query: str) -> list[dict[str, str]]:
        """
        Return a list of archived messages that best match the query.
        """
        return []

    def execute_function_call(self, db, function_name, arguments):
        """
        Dispatch function for function_name
        Takes:
          function_name - string
          arguments - dict build from json.loads
        Returns
          dict ready for json.dumps
        """
        # Default response value
        result = '{ "error": "' + f"no such function: {function_name}" + '" }'
        return result

    def funcError(self, error_string):
        return {"error": error_string}

    def funcStatus(self, status_string):
        return {"status": status_string}


def get_budgets(db):
    c = db.execute(
        "SELECT prompt_tokens, complete_tokens, "
        + " images FROM token_usage WHERE world_id = ?",
        ("limits",),
    )
    r = c.fetchone()
    if r is None:
        return {"prompt_tokens": 5_000_000, "complete_tokens": 2_000_000, "images": 100}
    (prompt, complete, images) = r
    return {"prompt_tokens": prompt, "complete_tokens": complete, "images": images}


def check_token_budgets(db):
    budgets = get_budgets(db)
    q = db.execute(
        "SELECT SUM(prompt_tokens), SUM(complete_tokens) "
        + "FROM token_usage WHERE world_id != ?",
        ("limits",),
    )
    (prompt_tokens, complete_tokens) = q.fetchone()
    return (
        prompt_tokens < budgets["prompt_tokens"]
        and complete_tokens < budgets["complete_tokens"]
    )


def check_image_budget(db):
    budgets = get_budgets(db)
    q = db.execute(
        "SELECT SUM(images) FROM token_usage WHERE world_id != ?", ("limits",)
    )
    (images,) = q.fetchone()
    return images < budgets["images"]


def ensure_token_entry(db, world_id):
    q = db.execute("SELECT COUNT(*) FROM token_usage WHERE world_id = ?", (world_id,))
    if q.fetchone()[0] == 0:
        db.execute("INSERT INTO token_usage VALUES (?, 0, 0, 0, 0)", (world_id,))


def count_image(db, world_id, count):
    ensure_token_entry(db, world_id)

    db.execute(
        "UPDATE token_usage SET images = images + ? " + "WHERE world_id = ?",
        (count, world_id),
    )
    db.commit()


def track_tokens(db, world_id, prompt_tokens, complete_tokens, total_tokens):
    ensure_token_entry(db, world_id)

    db.execute(
        "UPDATE token_usage SET prompt_tokens = prompt_tokens + ?, "
        + "complete_tokens = complete_tokens + ?, "
        + "total_tokens = total_tokens + ? WHERE world_id = ?",
        (prompt_tokens, complete_tokens, total_tokens, world_id),
    )
    db.commit()


def dump_token_usage(db):
    q = db.execute(
        "SELECT world_id, prompt_tokens, complete_tokens, "
        + "total_tokens FROM token_usage"
    )
    for world_id, prompt_tokens, complete_tokens, total_tokens in q.fetchall():
        print(
            f"world({world_id}): prompt: {prompt_tokens}, complete: "
            + f"{complete_tokens}, total: {total_tokens}"
        )

    print()
    q = db.execute(
        "SELECT SUM(prompt_tokens), SUM(complete_tokens), "
        + "SUM(total_tokens) FROM token_usage WHERE world_id != ?",
        ("limits",),
    )
    (prompt_tokens, complete_tokens, total_tokens) = q.fetchone()
    print(
        f"total: prompt: {prompt_tokens}, complete: "
        + f"{complete_tokens}, total: {total_tokens}"
    )
