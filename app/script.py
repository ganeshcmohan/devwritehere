# -*- coding: utf-8 -*-
from datetime import datetime
from flask import current_app
from flask.ext.script import Command, Option
from werkzeug.local import LocalProxy
from slugify import slugify
from . import models as m
from . import settings

_datastore = LocalProxy(lambda: current_app.extensions['security'].datastore)


def commit(fn):
    def wrapper(*args, **kwargs):
        fn(*args, **kwargs)
        _datastore.commit()
    return wrapper

class ImportTopicsCommand(Command):
    """import topics"""

    option_list = (
        Option('-f', '--fixture',    dest='fixture',    default=None),
    )

    @commit
    def run(self, **kwargs):
        line = 'advice wanted • education & school • film, tv, music & books • health & fitness • humour • love & relationships • my life • observations • people • politics • random thoughts • religion & faith • original fiction & poetry • social interactions • sports • technology • travel • true stories • writing & blogging'
        topics = [t.strip() for t in line.split('•')]
        #print 'rm all topics...'
        #m.Topic.objects.all().delete()
        for t in topics:
            slug = slugify(t)
            print t, "==>", slug
            obj = m.Topic.objects(slug=slug).first()
            if not obj:
                obj = m.Topic()
                print 'new topic created'
            else:
                print 'old topic updated'
            obj.topic = t
            obj.slug = slug
            obj.date_created = obj.date_updated = datetime(2000,1,1,0,0,0,0)
            obj.silent_save()

class ClearTopicsCommand(Command):

    @commit
    def run(self, **kwargs):
        for o in m.Post.objects.all():
            print o.headline
            o.topics = []
            o.save()
        #m.Topics.objects.all().delete()

class SendXmailCommand(Command):

    @commit
    def run(self, **kwargs):
        for o in m.Xmail.objects(done=False):
            o.send()

class AddThisUpdateCommand(Command):
    @commit
    def run(self, **kwargs):
        #for post in m.Post.objects().order_by('shares_updated'):
        for post in m.Post.objects:
            try:
                post.update_shares()
            except Exception,e:
                print e

class TestFBCommand(Command):

    @commit
    def run(self, **kwargs):
        import facebook as fb
        u = m.User.objects.get(email="guoqiao@gmail.com")
        c = m.SocialConnection.objects.get(user_id=u.id, service_alias='facebook')
        data = {'name': 'grapth test', 'link': 'http://writehere.com/post/140803-1/think', 'caption': "haha", 'description': "hihihihihi"}
        graph = fb.GraphAPI(c.access_token, version=settings.FACEBOOK_SDK_VERSION)
        graph.put_wall_post(message='a test', attachment=data)

class ExportPostsCommand(Command):

    option_list = (
        Option('-s', '--slug',  dest='slug',  default=None),
    )

    @commit
    def run(self, slug):
        from path import path
        root = path('~').expanduser()/'wh-posts-export'
        user = m.User.objects.get(date_slug=slug)
        home = root/slug
        home.makedirs_p()
        posts = m.Post.objects(user=user)
        for post in posts:
            name = '%s-%s.txt' % (post.date_slug, slugify(post.headline))
            output = home/name
            print output
            c = post.content.replace('<br>', '\n')
            try:
                output.write_text(c)
            except Exception, e:
                print e


def mongoengine_upgrade(doc):
    from mongoengine import Document
    if not issubclass(doc, Document):
        print 'not Document, skip'
        return
    if doc == Document:
        print 'is Document itself, skip'
        return
    collection = doc._get_collection()
    collection.update({}, {"$unset": {"_types": 1}}, multi=True)

    # 3. Confirm extra data is removed
    count = collection.find({'_types': {"$exists": True}}).count()
    assert count == 0

    # 4. Remove indexes
    info = collection.index_information()
    indexes_to_drop = [key for key, value in info.iteritems() if '_types' in dict(value['key'])]
    for index in indexes_to_drop:
        collection.drop_index(index)

    # 5. Recreate indexes
    doc.ensure_indexes()


class UpgradeMongoengineCommand(Command):
    """Upgrade mongoengine to 0.7 to 0.8"""

    @commit
    def run(self, **kwargs):
        import sys, inspect
        x = inspect.getmembers(sys.modules['app.models'], inspect.isclass)
        for name, doc in x:
            print 'mongoengine_upgrade:', name
            mongoengine_upgrade(doc)
