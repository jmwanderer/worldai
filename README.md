# worldai
AI assisted world builder and (someday) player


# Run dev / debug
## Server
- flask --app worldai.server run --debug

## Client
- cd worldai/ui
- npm install (one time)
- npm start

# Test
- make test

# Run dev server and built UI
- make build_ui
- flask --app worldai.server run --debug


# Build
- make build
- cp worldai-*.whl <dest>

# Configure to run

Setup config.py in instance directory:

- SECRET_KEY='DEV'
- AUTH_KEY='auth'
- OPENAI_API_KEY='the key'

