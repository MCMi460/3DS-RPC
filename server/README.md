# server

## Setup
In brief, copy `api/template.private.py` to `api/private.py` and edit accordingly.

## Database Migrations
[Flask-Migrate](https://flask-migrate.readthedocs.io/en/latest/index.html) is used for database migrations.
Please refer to its documentation for in-depth usage.

Please note that `server.py` is the Flask application currently used for migrations.
When interacting with `flask db`, you may have to specify it as the app:
```
flask --app server.py db [...]
```

As a general rule of thumb: whenever you see migrations added, please run them.
You can do so via the following command:
```
flask db upgrade
```

To create migrations:
```
flask db migrate -m "Migration reason"
```
