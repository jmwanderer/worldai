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

# Try Out Safely
In general it is not a good idea to download and run large code bases 
on your personal machine. It would be easy to search for and exfiltrate 
secret information on your PC (SSH keys, API keys, bitcoin wallets, etc).

Solution: use a VM to run untrusted software. virt-manager is a great
package on Linux for creating and running VMs.

It is also not a good idea to share your OpenAI API key. It is diffcult to
ensure software does't forward a secret key.

Possible solution: OpenAI project keys. Create a dedicated project with an API
key. Set budget limits and perhaps rate limits on the project to limit
the impact of any theft.

# Production Use
A good approach for hosting production applicaiton is to create
a dedicated user for each app.

## Build

Build a versoned Python distribution file for install.

Edit the version in pyproject.toml
- version = "0.2.0"

```
make build
cp dist/worldai-0.2.0-py3-none-any.whl <dest>
```

## Install and Configure for Production

```
mkdir worldai_app
cd worldai
python -m venv venv
source ./venv/bin/activate
pip install worldai-0.2.0-py3-none-any.whl <dest>
```

Configure the Flask secret key and the OpenAI API key in
config.py.  Setup config.py in instance directory:

```
cd worldai_app/venv
mkdir -p var/worldai.server-instance/
vi config.py
```

- SECRET_KEY='generate a secret string'
- OPENAI_API_KEY='the key'

A good way to generate a secret string:
```
python3
import os
os.urandom(32).hex()
```

## Run a production server

A good configuration for running a production server is:
- Use a WSGI server to host the app (e.g. waitress or gunicorn)
- Use Apache2 or NGINX as a front end server

### Run app  in a WSGI server

Example: waitress running the worldai server on port 8085

```
cd worldai_app
. ./venv/bin/activate
pip install waitress
python3 -m waitress --threads=5 --port 8085 --call worldai.server:create_app
```

### Run a FrontEnd 

- Add ProxyPass and ProxyPassReverse to sites file:
```
    ProxyPass /worldai http://127.0.0.1:8085
    ProxyPassReverse /worldai http://127.0.0.1:8085
```

- Run App with a url-prefix
```
python3 -m waitress --threads=5 --url-prefix=worldai --port 8085 --call worldai.server:create_app
```

### Auto Startup
WIP

Configure worldai.service

or

crontab @reboot
