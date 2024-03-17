# Story Quest
StoryQuest is a GPT-AI driven world builder and story player.

# Contents
| Item                          | Description                                           |
| ----------------------------- | ----------------------------------------------------- |
| /worldai                      | Python sources files for a Flask based service.   |
| /tests                        | Pytest unit tests                                 |
| /worldai/ui                   | React based Design and Player UIs                 |

# Architecture

A nominally restful API serving:
- Definitions of worlds, characters, sites, and items
- Instances of worlds, characters, sites, and items
- Operations to move locations, engage and converse with characters

GPT use for character conversations, includes:
- Actions for character to take: move, pick up, use, ...
- Information lookup for characters to use in response

sqlite3 database

# Requirements

## Python
StoryQuest requires flask and other modules.
```
pip install requirements.txt
```
Consider using a virtual env.

## React
Install the npm packages prior to building:

```
cd worldai/ui
npm install
```

# Run Development / Debug Mode
## Server
```
export OPENAI_API_KEY="secret key"
flask --app worldai.server run --debug
```

Add a user entry for access:
```
flask --app worldai.server add-user jim
```

Output:
```
Added user jim. Auth key = f3625fcdab32159bd0874364
```



## Client

Set an environment variable for the client's auth key and run the client in 
debug mode:
```
export VITE_AUTH_KEY="auth key value"
cd worldai/ui
npm run dev
```
Connect to: http://localhost:5173

## Run Debug Server and Built UIs
```
make build_ui
flask --app worldai.server run --debug
```

Connect to http://localhost:5000

Use the auth key value to login to the client when prompted for an auth key.

## Test
```
make test
```

# Production Use

## Build
```
make build
cp worldai-*.whl <dest>
```

## Install and Configure for Production

```
pip install worlai-....whl
```

Setup config.py in instance directory:

- SECRET_KEY='generate a secret string'
- OPENAI_API_KEY='the key'

## Run a production server

TODO: run with waitress or gunicorn

