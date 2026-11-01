---
slug: first-fastapi-app
title: Your first FastAPI app
position: 2
published: true
exercise:
  kind: local
  steps:
    - instruction: |
        Create a folder for the project and move into it.
      command: |
        mkdir hello-api
        cd hello-api
      expected_output: |
        No errors. Your prompt now ends with hello-api.
      check: Your PowerShell prompt shows hello-api as the current folder.

    - instruction: |
        Create a virtual environment and activate it. A virtual environment keeps this project's packages separate from everything else on your machine.

        If PowerShell refuses to run the activate script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.
      command: |
        python -m venv .venv
        .\.venv\Scripts\Activate.ps1
      expected_output: |
        Your prompt now starts with (.venv).
      check: The (.venv) marker appears at the start of your prompt.

    - instruction: |
        Install FastAPI. The standard extra also installs the web server and the `fastapi` command.
      command: |
        pip install "fastapi[standard]"
        pip show fastapi
      expected_output: |
        The install ends with a line starting "Successfully installed", and pip show prints Name: fastapi followed by a Version line.
      check: pip show fastapi prints a version number.

    - instruction: |
        Create a file called main.py in the hello-api folder with this content, then save it.

        ```python
        from fastapi import FastAPI

        app = FastAPI()


        @app.get("/")
        def read_root():
            return {"message": "Hello"}
        ```
      command: |
        notepad main.py
      expected_output: |
        The file main.py exists in the hello-api folder.
      check: Running dir lists main.py.

    - instruction: |
        Start the development server. Leave this window open and running.
      command: |
        fastapi dev main.py
      expected_output: |
        Several lines of startup messages, including a line like
        Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
      check: You see the Uvicorn running line and no error message.

    - instruction: |
        Open a second PowerShell window and call your API. Then open the interactive docs in your browser.
      command: |
        Invoke-WebRequest http://127.0.0.1:8000/ | Select-Object -ExpandProperty Content
        Start-Process "http://127.0.0.1:8000/docs"
      expected_output: |
        {"message":"Hello"}
      check: The first command printed the message and the browser shows the Swagger docs page. Press Ctrl+C in the server window to stop it.
---
## What FastAPI is

FastAPI is a Python framework for building web APIs. You write ordinary Python functions, and FastAPI turns them into HTTP endpoints, validates the data going in and out, and generates interactive documentation for free.

## The smallest app

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Hello"}
```

Three things are happening here:

- `app = FastAPI()` creates the application object. Everything else attaches to it.
- `@app.get("/")` is a **decorator** that registers the function below it as the handler for `GET /`. The method comes from the decorator name and the path from its argument.
- The function returns a Python dictionary, and FastAPI converts it to JSON for you.

## Running it

```text
fastapi dev main.py
```

This starts a development server on port 8000 and reloads it every time you save the file. FastAPI also serves automatic documentation at `/docs`, where you can try each endpoint from the browser.

## Common problems

- **`fastapi` is not recognized:** your virtual environment is not active. Activate it again and check for `(.venv)` in the prompt.
- **Activate.ps1 cannot be loaded:** PowerShell's execution policy is blocking scripts. The exercise shows the one-time fix.
- **Address already in use:** an earlier server is still running. Stop it with Ctrl+C in its window.