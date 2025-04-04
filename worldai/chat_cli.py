"""
Client to run chat from the CLI for testing

    Jim Wanderer
    http://github.com/jmwanderer
"""


import logging

from . import chat, chat_functions, db_access


def get_user_input():
    return input("> ").strip()


def chat_loop():
    db = db_access.open_db()
    logging.info("\nstartup*****************")
    print("Test chat client")
    chat_session = chat.ChatSession()

    while True:
        try:
            user = get_user_input()
        except EOFError:
            break
        if user == "exit":
            break
        if len(user) == 0:
            continue

        if user.startswith("system:"):
            system = user[user.index(":") + 1 :].strip()
            print(f"system message {system}")
            result = chat_session.chat_exchange(db, system=system)
        else:
            result = chat_session.chat_exchange(db, user=user)

        assistant_message = result.reply
        text = result.updates
        print(assistant_message)
        if len(text) > 0:
            print(text)

    # chat.pretty_print_conversation(BuildMessages(message_history))
    print(chat_session.chat_history()["messages"])
    print("Tokens")

    print("\nRunning total")
    chat_functions.dump_token_usage(db)
    db.close()
