---
slug: what-is-an-api
title: What is an API?
position: 1
published: true
---
## The idea

An API (application programming interface) is a way for one program to ask another program to do something. In web development, the two programs are usually a **client** (a browser, a mobile app, a script) and a **server** (your backend). They talk over HTTP.

The client sends a **request**. The server sends back a **response**.

## A request and a response

A request says what the client wants:

```http
GET /users/42 HTTP/1.1
Host: api.example.com
Accept: application/json
```

The response says how it went and carries the data:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"id": 42, "name": "Asha"}
```

Three parts matter in every exchange:

- **Method and path**: what to do (`GET`) and to which resource (`/users/42`).
- **Status code**: a number that summarises the outcome (`200` means OK).
- **Body**: the data, almost always JSON for the APIs you will build.

## HTTP methods

| Method | Typical use |
| --- | --- |
| GET | Read data. Should not change anything. |
| POST | Create something new. |
| PUT / PATCH | Replace or partially update something. |
| DELETE | Remove something. |

## Status codes you will use constantly

| Code | Meaning |
| --- | --- |
| 200 | OK |
| 201 | Created |
| 204 | Success, nothing to return |
| 400 | The request was malformed |
| 401 | Not logged in |
| 404 | Not found |
| 422 | The data was well-formed but failed validation |
| 500 | Your server crashed |

## What a backend actually does

Your backend receives requests, checks who is asking, validates the data, talks to a database, and builds the response. The rest of this course teaches each of those jobs, one at a time, using FastAPI.