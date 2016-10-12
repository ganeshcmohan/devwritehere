from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.mail import Mail
from flask.ext.mongoengine import MongoEngine
from flask.ext.cache import Cache
from settings import HTTP_EXTERNAL_BASE
from celery import Celery

domain = HTTP_EXTERNAL_BASE.split('//')[1]
cache = Cache()
sql = SQLAlchemy()
mail = Mail()
db = MongoEngine()

celery = Celery()
