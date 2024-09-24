# server

## Setup
In brief, copy `api/template.private.py` to `api/private.py` and edit accordingly.

## Database Migrations
[Flask-Migrate](https://flask-migrate.readthedocs.io/en/latest/index.html) is used for database migrations.
Please refer to its documentation for in-depth usage.


Regarding this project, `server.py` is the Flask application currently used for migrations.
When interacting with `flask db`, you may have to specify it as the app:
```
flask --app server.py db [...]
```
