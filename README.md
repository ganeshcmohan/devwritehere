# How to run site on mac for dev

- install mongodb 2.4.x version
- download dump data here: http://static.writehere.com/
- mongorestore data
- run mongodb:

    mongod

- install redis
- run redis:

    redis-server

- create virtualenv
- in venv, run this:

    pip install -r requirements.txt && pip uninstall simplejson

Some how there will be 2 different simplejson versions, need to uninstall one to fix it.

- run the site:

    python manage.py runserver

- watch and compile sass:

    cd app/static/
    ./watch.sh

