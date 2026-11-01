---
slug: path-and-query-parameters
title: Path and query parameters
position: 1
published: true
exercise:
  kind: local
  steps:
    - instruction: |
        Continue in the hello-api folder with the virtual environment active. Replace the contents of main.py with this and save it.

        ```python
        from fastapi import FastAPI

        app = FastAPI()


        @app.get("/")
        def read_root():
            return {"message": "Hello"}


        @app.get("/items/{item_id}")
        def read_item(item_id: int, q: str | None = None):
            return {"item_id": item_id, "q": q}
        ```
      command: |
        notepad main.py
      expected_output: |
        main.py now contains both routes.
      check: The file has a read_root and a read_item function.

    - instruction: |
        Start the server if it is not running already, and leave it open.
      command: |
        fastapi dev main.py
      expected_output: |
        A line like Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
      check: The server started without errors.

    - instruction: |
        In a second PowerShell window, call the endpoint with a path parameter.
      command: |
        Invoke-WebRequest "http://127.0.0.1:8000/items/5" | Select-Object -ExpandProperty Content
      expected_output: |
        {"item_id":5,"q":null}
      check: item_id is the number 5, not the text "5", and q is null.

    - instruction: |
        Now add a query parameter after the question mark.
      command: |
        Invoke-WebRequest "http://127.0.0.1:8000/items/5?q=hello" | Select-Object -ExpandProperty Content
      expected_output: |
        {"item_id":5,"q":"hello"}
      check: q now contains hello.

    - instruction: |
        Send something that is not a number as the item id. This opens your browser, because PowerShell treats the 422 response as an error.
      command: |
        Start-Process "http://127.0.0.1:8000/items/abc"
      expected_output: |
        A JSON error body with a "detail" list. The first entry has "loc" ["path","item_id"] and a message saying the input should be a valid integer. Extra keys may appear.
      check: You got a validation error instead of a crash, and the server window shows a 422 response.
---
## Two ways to receive input

Most endpoints need some input from the request URL. FastAPI gives you two kinds, and it tells them apart by how you write the function.

```python
@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}
```

- **Path parameters** appear inside braces in the path, like `{item_id}`. The function parameter must have the same name. They identify *which* resource you mean: `/items/5`.
- **Query parameters** are function parameters that are *not* in the path. They come after `?` in the URL, as in `/items/5?q=hello`, and are usually filters or options.

## Required or optional

A parameter without a default value is required. Giving it a default makes it optional:

```python
def read_item(item_id: int, q: str | None = None):
```

Here `item_id` is required (it is part of the path), and `q` is optional because it defaults to `None`.

## Types do real work

The type hint `item_id: int` is not decoration. FastAPI uses it to convert and validate the value:

- `/items/5` gives your function the integer `5`.
- `/items/abc` never reaches your function. FastAPI answers `422` with an error that explains what was wrong and where.

This validation is powered by Pydantic, which you will meet properly in a later lesson.

## Order of routes matters

FastAPI checks routes in the order you define them. If you had both `/items/{item_id}` and a fixed path such as `/items/latest`, the fixed one must come first, or `latest` would be treated as an `item_id`.

## See it in the docs

Open `/docs` while the server runs. Both parameters appear there, with their types, and you can try requests from the page without writing any client code.