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
export OPENAI_API_KEY='secret key'
flask --app worldai.server run --debug
```

TODO: add user command

## Client
```
cd worldai/ui
npm start
```
Connect to: http://localhost:5173

## Run Debug Server and Built UIs
```
make build_ui
flask --app worldai.server run --debug
```

Connect to http://localhost:5000


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

Setup config.py in instance directory:

- SECRET_KEY='generate a secret string'
- OPENAI_API_KEY='the key'

TODO: add user command

TODO: run with waitress

