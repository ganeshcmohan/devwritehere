import json
import requests
from time import sleep
from flask import url_for, current_app
from bson.objectid import ObjectId
from mongoengine import Document, StringField, ReferenceField
from mongoengine import ListField, BooleanField, IntField, DateTimeField
from mongoengine import FileField, ObjectIdField, CASCADE, DictField
from flask.ext.security import UserMixin, RoleMixin, AnonymousUser
from flask.ext.security.utils import encrypt_password
from flask.ext.mail import Message
from extensions import mail

from extensions import sql, cache
from util import extract_chars, br2nl, unclean_breaks, nl2br
from slugify import slugify
from calendar import timegm
from random import choice
from datetime import datetime, timedelta
import pytz, uuid
from six.moves import html_parser

from settings import ADDTHIS_SHARES_URL, LONG_URL_OPINION, SHORT_URL_OPINION, TOPIC_NEW_DATE

PW_SYMBOLS = 'abcdefghijklmnopqrstuvwxyz123456789'

ADDTHIS_INTERVAL = timedelta(hours=4)

h = html_parser.HTMLParser()

class SQLMailBox(sql.Model):
    __tablename__ = 'mailbox'

    username = sql.Column(sql.String(255), primary_key=True)
    password = sql.Column(sql.String(255))
    name = sql.Column(sql.String(255))
    maildir = sql.Column(sql.String(255))
    quota = sql.Column(sql.BigInteger(), default=0)
    local_part = sql.Column(sql.String(255))
    domain = sql.Column(sql.String(255))
    created = sql.Column(sql.DateTime, default=datetime.utcnow())
    modified = sql.Column(sql.DateTime, default=datetime.utcnow())
    active = sql.Column(sql.SmallInteger(), default=1)

class Xmail(Document):
    subject = StringField()
    body = StringField()
    sender = StringField()
    recipients = ListField()
    create = DateTimeField()
    modified = DateTimeField() # joe: was modify before, but not allowed in new version
    minutes = IntField(default=60)
    done = BooleanField(default=False)

    def __unicode__(self):
        return '%s to %s' % (self.subject, ','.join(self.recipients))

    def save(self, *args, **kargs):
        self.modify = datetime.now()
        if not self.create:
            self.create = self.modify
        super(Xmail, self).save(*args, **kargs)

    def due(self):
        now = datetime.now()
        delta = timedelta(minutes=self.minutes)
        return now - self.create >= delta

    def send(self):
        print self
        if self.due():
            msg = Message(
                self.subject,
                sender=self.sender,
                recipients=self.recipients,
            )

            msg.body = self.body
            msg.html = self.body
            mail.send(msg)
            self.done = True
            self.save()
            print 'sent'
        else:
            print 'wait'

class UniqueCounter(Document):
    counter = StringField(primary_key=True, unique=True)
    sequence = IntField(default=0)

class Role(Document, RoleMixin):
    name = StringField(required=True, unique=True, max_length=80)
    description = StringField(max_length=255)

class Connection(Document):
    user_id = ObjectIdField()
    provider_id = StringField(max_length=255)
    provider_user_id = StringField(max_length=255)
    access_token = StringField(max_length=255)
    secret = StringField(max_length=255)
    display_name = StringField(max_length=255)
    profile_url = StringField(max_length=512)
    image_url = StringField(max_length=512)
    rank = IntField(default=1)

    @property
    def user(self):
        return User.objects(id=self.user_id).first()

class SocialConnection(Document):
    service_alias = StringField()
    service_id = StringField()
    access_token = StringField()
    secret = StringField()
    expires = DateTimeField()
    refresh_token = StringField()
    user_id = ObjectIdField()
    verifier = StringField(default='')
    contact_info = StringField(default='')

    @property
    def user_contact(self):
        if not self.contact_info:
            return self.service_id
        return self.contact_info

    @property
    def user(self):
        return User.objects(id=self.user_id).first()

    def __unicode__(self):
        return self.service_alias

    def __repr__(self):
        return '<SocialConnection %s %s>' % (self.service_alias, self.service_id)

    def is_expired(self):
        return self.expires and self.expires < datetime.now()

class User(Document, UserMixin):
    meta = {
        'indexes': ['verification_uuid', 'email', 'username'],
        'ordering': ['-date_created'],
    }

    email = StringField(unique=True, max_length=255)
    username = StringField(max_length=255)
    password = StringField(required=True, max_length=255)
    active = BooleanField(default=True)
    remember_token = StringField(max_length=255)
    authentication_token = StringField(max_length=255)
    roles = ListField(ReferenceField(Role, dbref=False), default=[])
    oauth_only = BooleanField(default=False)

    verified = BooleanField(default=False)
    verification_uuid = StringField(default=str(uuid.uuid4()))
    reset_uuid = StringField(default=str(uuid.uuid4()))

    avatar = FileField()
    avatar_full = FileField()
    crop_photo = FileField()
    crop_photo_orientation = StringField()

    date_created = DateTimeField()
    date_updated = DateTimeField()
    date_slug = StringField()

    requires_refresh = BooleanField(default=False)

    last_click_followers = DateTimeField(default=datetime(2014,9,14))
    last_click_comments = DateTimeField(default=datetime(2014,9,14))

    def __unicode__(self):
        return self.username or self.email

    def avatar_url(self):
        if self.avatar:
            return url_for('media.show_avatar',user_id=self.id)
        else:
            return '/static/img/avatar.png'

    def delete(self, *args, **kwargs):
        """ delete associated records first, to prevent orphans """

        """ remove any social connections """
        connections = SocialConnection.objects(user_id=self.id)
        for con in connections:
            con.delete()

        """ remove any comments """
        comments = Comment.objects(user=self.id)
        for comment in comments:
            comment.delete()

        """ remove any posts """
        posts = Post.objects(user=self.id)
        for post in posts:
            post.delete()

        """ remove files from gridfs """
        if self.avatar:
            self.avatar.delete()
        if self.avatar_full:
            self.avatar_full.delete()
        if self.crop_photo:
            self.crop_photo.delete()

        profile = Profile.objects(user=self.id)
        profile.delete()

        super(User, self).delete(*args, **kwargs)

    @property
    def is_admin(self):
        for role in self.roles:
            if role.name == 'admin':
                return True
        return False

    @property
    def is_super(self):
        for role in self.roles:
            if role.name == 'super':
                return True
        return False

    def set_role(self, role_name):
        role = Role.objects.get(name=role_name)
        if role not in self.roles:
            self.roles.append(role)
            self.save()

    def set_admin(self):
        self.set_role('admin')

    def set_super(self):
        self.set_role('super')

    @property
    def verification_link(self):
        return self.verification_uuid

    def create(self, *args, **kwargs):
        dt_string = self.date_created.strftime('%y%m%d')
        counter = 'user' + dt_string
        post_counter = UniqueCounter.objects(counter=counter).modify(upsert=True, new=True, inc__sequence=1)
        self.date_slug = dt_string + '-' + str(post_counter.sequence)
        return self.save(*args, **kwargs)

    def save(self, *args, **kargs):
        self.date_updated = datetime.utcnow()
        if not self.date_created:
            self.date_created = self.date_updated
        super(User, self).save(*args, **kargs)

    def generate_password(self):
        self.password = encrypt_password(''.join(choice(PW_SYMBOLS) for _ in xrange(8)))

    def set_password(self, plain_password):
        self.password = encrypt_password(plain_password)
        self.save()

    @property
    def my_page_anchor(self):
        try:
            return extract_chars(unicode(self.profile.display_name) + ', ' + unicode(self.profile.location or ''), 30)
        except:
            return 'Unknown'

    @property
    def my_page_url(self):
        return url_for('write.my_page',
                date_slug=self.date_slug,
                display_name_slug=self.display_name_slug)

    def new_followers(self):
        return UserRelation.objects(user=self, date_created__gt=self.last_click_followers).count()

    def new_comments(self):
        return Comment.objects(post__user=self, date_created__gt=self.last_click_comments).count()

    @property
    def followers_url(self):
        return url_for('write.followers',
                date_slug=self.date_slug,
                display_name_slug=self.display_name_slug)

    @property
    def following_url(self):
        return url_for('write.following',
                date_slug=self.date_slug,
                display_name_slug=self.display_name_slug)

    @property
    def display_name_slug(self):
        profile = Profile.objects(user=self).first()
        if profile:
            return slugify(profile.display_name)
        else:
            return 'unknown'

    @property
    def slug(self):
        profile = Profile.objects(user=self).first()
        if profile:
            return slugify(profile.display_name)
        else:
            return 'unknown'

    @property
    def opinion_count(self):
        post_count = Post.objects(user=self, is_spam__ne=True, is_draft__ne=True).count()
        return int(post_count)

    @property
    def comment_count(self):
        comment_count = Comment.objects(user=self).count()
        return int(comment_count)

    @property
    def follower_count(self):
        count = UserRelation.objects(user=self).count()
        return int(count)

    @property
    def following_count(self):
        count = UserRelation.objects(follower=self).count()
        return int(count)

    def followers(self):
        rx = UserRelation.objects(user=self)
        return [r.follower for r in rx]

    def following(self):
        rx = UserRelation.objects(follower=self)
        return [r.user for r in rx]

    @property
    def profile(self):
        profile = Profile.objects(user=self).first()
        return profile

    def is_following(self, user_id):
        relation = UserRelation.objects(user=ObjectId(user_id), follower=self).first()
        if not relation:
            return False
        return True

    @property
    def contact_list(self):
        """ get any social connections """
        contacts = []

        if not self.oauth_only:
            contacts.append(('E-mail', self.email,))

        connections = SocialConnection.objects(user_id=self.id)
        for con in connections:
            if not con.contact_info:
                contact_info = con.service_id
            else:
                contact_info = con.contact_info
            contacts.append((con.service_alias, contact_info,))

        return contacts

    @property
    def formatted_date(self):
        d = self.date_created
        month = d.strftime('%b')
        return '{month} {d.day}, {d.year}'.format(
            d=d,
            month=month,
        )

    @property
    def has_twitter(self):
        return SocialConnection.objects(user_id=self.id, service_alias='twitter').count() > 0

    @property
    def has_facebook(self):
        return SocialConnection.objects(user_id=self.id, service_alias='facebook').count() > 0

    @property
    def has_google(self):
        return SocialConnection.objects(user_id=self.id, service_alias='google').count() > 0

    @property
    def has_linkedin(self):
        return SocialConnection.objects(user_id=self.id, service_alias='linkedin').count() > 0

    @property
    def social_connections(self):
        return SocialConnection.objects(user_id=self.id)

class AnonymousUser(AnonymousUser, UserMixin):

    email = StringField(unique=True, max_length=255)
    password = StringField(required=True, max_length=255)
    active = BooleanField(default=False)
    remember_token = StringField(max_length=255)
    authentication_token = StringField(max_length=255)
    requires_refresh = BooleanField(default=False)

    @property
    def id(self):
        return None

    @property
    def is_authenticated(self):
        return False

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return True

    @property
    def display_name_slug(self):
        return ''

    @property
    def slug(self):
        return ''

    @property
    def opinion_count(self):
        return 0

    @property
    def follower_count(self):
        return 0

    @property
    def profile(self):
        return dict()

    def is_following(self, user_id):
        return False

class Profile(Document):
    user = ReferenceField(User, dbref=False)
    display_name = StringField()
    location = StringField()
    web_presence = StringField()
    bio =  StringField()
    first_login = BooleanField(default=True)
    photo = FileField()

    date_created = DateTimeField()
    date_updated = DateTimeField()

    def show_web_presence(self):
        return unclean_breaks(self.web_presence)

    def show_bio(self):
        return nl2br(self.bio)

    @property
    def location_line(self):
        return self.location or 'Unknown'

    def save(self, *args, **kargs):
        self.date_updated = datetime.utcnow()
        if not self.date_created:
            self.date_created = self.date_updated

        super(Profile, self).save(*args, **kargs)

class Topic(Document):

    meta = {
        'indexes': ['-date_updated_timestamp', '-posts', '-views'],
        'ordering': ['-date_created','topic'],
    }

    topic = StringField(required=True)
    slug = StringField()
    views = IntField(default=0)
    posts = IntField(default=0)
    comments = IntField(default=0)
    date_created = DateTimeField()
    date_updated = DateTimeField()
    date_updated_timestamp = IntField(default=0)

    def __unicode__(self):
        return self.topic

    def is_new(self):
        return self.date_created == TOPIC_NEW_DATE

    @property
    def post(self):
        return Post.objects(topics=self.id, is_spam__ne=True, is_draft__ne=True).order_by('-weight', 'id').first()

    def post_set(self):
        return Post.objects(topics=self.id)

    def sync_posts_count(self):
        self.posts = self.post_set().count()
        self.save()

    @property
    def photo_url(self):
        post = self.post
        if post:
            if self.post.photo:
                return url_for('media.post_photo', post_id=self.post.id)

        post = Post.objects(topics=self.id, is_spam__ne=True, is_draft__ne=True, photo__ne=None).order_by('-views').only('photo').first()
        if post and post.photo:
            return url_for('media.post_photo', post_id=post.id)
        else:
            return None

    @property
    def photo_orientation(self):
        post = Post.objects(topics=self.id, is_spam__ne=True, is_draft__ne=True).order_by('-views').only('photo').first()
        if post.photo:
            return post.photo_orientation
        else:
            return None

    @property
    def timestamp(self):
        return timegm(self.date_updated.utctimetuple())

    def save(self, *args, **kargs):
        #self.date_updated = datetime.utcnow()
        if not self.date_created:
            self.date_created = datetime.utcnow()
        self.slug = slugify(self.topic)
        super(Topic, self).save(*args, **kargs)

    def silent_save(self, *args, **kwargs):
        super(Topic, self).save(*args, **kwargs)

    def update_timestamp(self):
        self.date_updated = datetime.utcnow()
        self.date_updated_timestamp = int(timegm(self.date_updated.utctimetuple()))

class Post(Document):

    meta = {
        'indexes': ['-date_updated_timestamp', '-comment_increment', '-views'],
        'ordering': ['-date_created'],
    }

    user = ReferenceField(User, dbref=False)
    headline = StringField(max_length=120, required=True)
    content = StringField()
    extract = StringField()
    topics = ListField(ReferenceField(Topic, dbref=False))
    photo = FileField()
    photo_orientation = StringField(default=None)
    photo_source = StringField(default=None)
    views = IntField(default=0)
    flagged = ListField()
    date_slug = StringField()

    date_created = DateTimeField()
    date_updated = DateTimeField()
    date_updated_timestamp = IntField(default=0)
    comment_increment = IntField(default=0)
    weight = IntField(default=0)
    topic_weight = StringField(default=0)
    is_spam = BooleanField(default=False)
    is_draft = BooleanField(default=False)

    facebook_post = BooleanField(default=False)
    linkedin_post = BooleanField(default=False)
    twitter_post = BooleanField(default=False)

    shares = IntField(default=0)
    shares_updated = DateTimeField(default=datetime.utcnow)

    def __str__(self):
        return self.headline

    def __unicode__(self):
        return self.headline

    def update_topics(self):
        @cache.cached(timeout=300, key_prefix='update_topics_' + str(self.id))
        def cached_update_topics():
            from tasks import update_topic_counts
            for topic in self.topics:
                update_topic_counts.apply_async([str(topic.id)])
            return True

        cached_update_topics()

    @property
    def topic_list(self):
        return [{'name': topic.topic, 'url': url_for('show_topic', slug=topic.slug)} for topic in self.topics]

    def related_posts(self):
        return Post.objects(topics__in=self.topics,headline__ne=self.headline,
                is_spam__ne=True, is_draft__ne=True)[:20]

    @property
    def formatted_date(self):
        d = self.date_created
        month = d.strftime('%b')
        #am_pm = d.strftime('%p').lower()
        #hour = d.strftime('%I').lstrip('0')
        # {hour}.{d.minute:02}{am_pm},
        return '{month} {d.day}, {d.year}'.format(
            d=d,
            month=month,
        )
        #return self.date_created.strftime('%I.%M%p, %b %d, %Y')

    @property
    def popular_topic(self):
        topic_ids = [topic.id for topic in self.topics]
        return Topic.objects(id__in=topic_ids).order_by('-posts').first()

    @property
    def comments(self):
        return Comment.objects(post=self.id, is_spam=False).count()

    @property
    def url(self):
        return url_for('write.post', date_slug=self.date_slug, post_slug=self.slug)

    @property
    def short_url(self):
        return SHORT_URL_OPINION % {'code': self.date_slug }

    @property
    def photo_url(self):
        if self.photo:
            return url_for('media.post_photo', post_id=self.id)
        else:
            return None

    @property
    def photo_url_external(self):
        if self.photo:
            return url_for('media.post_photo', post_id=self.id)
        else:
            return url_for('static', filename='img/wh.jpg')

    @property
    def timestamp(self):
        return timegm(self.date_updated.utctimetuple())

    @property
    def slug(self):
        return slugify(self.headline).strip('-')

    @property
    def first_topic(self):
        return str(self.topics[0].topic)

    def create(self, *args, **kwargs):
        if not self.date_created:
            self.date_created = datetime.utcnow()
        dt_string = self.date_created.strftime('%y%m%d')
        counter = 'post'+ dt_string
        post_counter = UniqueCounter.objects(counter=counter).modify(upsert=True, new=True, inc__sequence=1)
        self.date_slug = dt_string + '-' + str(post_counter.sequence)
        if self.is_spam or self.is_draft:
            self.remove_from_search()
        return self.save(*args, **kwargs)

    def set_spam(self, is_spam):
        self.is_spam = is_spam
        self.flagged = filter(lambda x: x != 'spam', self.flagged)
        if is_spam:
            self.remove_from_search()
            for topic in self.topics:
                topic.posts -= 1
                topic.comments -= self.comments
                topic.silent_save()

        else:
            self.add_to_search()
            for topic in self.topics:
                topic.posts += 1
                topic.comments += self.comments
                topic.silent_save()
        self.save()



    def remove_from_search(self):
        """ remove from search index """
        try:
            with current_app.app_context():
                current_app.es.delete('opinions/opinion/%s' % str(self.id))
                current_app.es.post('_flush', data={'refresh': True})
        except:
            pass

    def add_to_search(self):
        """ add to search engine index """
        try:
            with current_app.app_context():
                topics = [topic.topic for topic in self.topics]

                current_app.es.put('opinions/opinion/%s' % str(self.id), data= {
                    'post_id': str(self.id),
                    'date_created': self.date_created.replace(tzinfo=pytz.UTC),
                    'content': br2nl(self.content),
                    'headline': br2nl(self.headline),
                    'topics': list(topics),
                    'author_name': str(self.user.profile.display_name),
                    'url': self.url,
                    })
        except:
            pass

    def delete(self, *args, **kwargs):

        """ decrement post counter on topics """
        if not self.is_spam:
            for topic in self.topics:
                topic.posts -= 1
                topic.comments -= self.comments
                topic.silent_save()

        """ remove photo from gridfs """
        if self.photo:
            self.photo.delete()

        self.remove_from_search()

        super(Post, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.date_updated = datetime.utcnow()
        if not self.date_created:
            self.date_created = self.date_updated
        self.date_updated_timestamp = int(timegm(self.date_updated.utctimetuple()))
        self.comment_increment = self.comments
        self.topic_weight = str(str(self.weight) + '_' + str(self.id))
        self.content = h.unescape(self.content.replace('<br />','<br>'))

        if not self.extract:
            self.extract = extract_chars(self.content, 150)

        super(Post, self).save(*args, **kwargs)

        if not self.is_spam and not self.is_draft:
            self.add_to_search()
        else:
            self.remove_from_search()

    def silent_save(self, *args, **kwargs):
        self.content = self.content.replace('<br />','<br>')
        super(Post, self).save(*args, **kwargs)

    def is_new(self):
        d = datetime.utcnow() - self.date_created
        return d < ADDTHIS_INTERVAL

    def is_shares_new(self):
        d = datetime.utcnow() - self.shares_updated
        return d < ADDTHIS_INTERVAL

    def should_update_shares(self):
        is_new = self.is_new()
        is_shares_new = self.is_shares_new()
        if not is_new and is_shares_new:
            return False
        return True

    def update_shares(self):
        post = self
        data = {
            'code': post.date_slug,
            'slug': post.slug
        }
        long_url = LONG_URL_OPINION % data
        short_url = SHORT_URL_OPINION % data

        url1 = ADDTHIS_SHARES_URL % {'url': long_url}
        long_r = requests.get(url1)
        sleep(1)
        url2 = ADDTHIS_SHARES_URL % {'url': short_url}
        short_r = requests.get(url2)
        sleep(1)
        print url1, url2
        #if long_r.status_code not in (200,) or short_r.status_code not in (200,): continue

        long_json = json.loads(long_r.text)
        short_json = json.loads(short_r.text)

        total_shares = int(long_json.get('shares', 0)) + int(short_json.get('shares', 0))
        if total_shares > 0:
            print total_shares

        post.shares = total_shares
        post.shares_updated = datetime.utcnow()
        post.silent_save()

class Comment(Document):
    meta = {
        'ordering': ['-date_created'],
    }
    user = ReferenceField(User, dbref=False)
    post = ReferenceField(Post, reverse_delete_rule=CASCADE, dbref=False)
    comment = StringField()
    extract = StringField()
    has_changed = BooleanField(default=False)

    date_created = DateTimeField()
    date_updated = DateTimeField()

    thumb_count = IntField(default=0)
    flagged = ListField()
    is_spam = BooleanField(default=False)

    def __unicode__(self):
        return self.comment

    @property
    def display_date(self):
        d = self.date_created
        month = d.strftime('%b')
        #am_pm = d.strftime('%p').lower()
        #hour = d.strftime('%I').lstrip('0')
        #{hour}.{d.minute:02}{am_pm},
        return '{month} {d.day}, {d.year}'.format(
            d=d,
            month=month
        )

    def save(self, *args, **kargs):
        if int(self.thumb_count) < 1:
            self.date_updated = datetime.utcnow()
        if not self.date_created:
            self.date_created = self.date_updated
        
	self.extract = self.extract.strip('<br>').strip()
 	self.has_changed = self.extract not in h.unescape(self.post.content).strip('<br>').strip()
        super(Comment, self).save(*args, **kargs)

    def silent_save(self, *args, **kwargs):
        super(Comment, self).save(*args, **kwargs)

    def set_spam(self, is_spam):
        self.is_spam = is_spam
        self.flagged = filter(lambda x: x != 'spam', self.flagged)
        if is_spam:
            for topic in self.post.topics:
                topic.comments -= 1
                topic.save()
        else:
            for topic in self.post.topics:
                topic.comments += 1
                topic.save()
        self.save()

class Reply(Document):
    meta = {
        'ordering': ['-date_created'],
    }
    user = ReferenceField(User, dbref=False)
    comment = ReferenceField(Comment, reverse_delete_rule=CASCADE, dbref=False)
    reply = StringField()

    date_created = DateTimeField()

    flagged = ListField()
    is_spam = BooleanField(default=False)

    def __unicode__(self):
        return self.reply

    def silent_save(self, *args, **kwargs):
        super(Reply, self).save(*args, **kwargs)

    @property
    def display_date(self):
        d = self.date_created
        month = d.strftime('%b')
        #am_pm = d.strftime('%p').lower()
        #hour = d.strftime('%I').lstrip('0')
        #{hour}.{d.minute:02}{am_pm},
        return '{month} {d.day}, {d.year}'.format(
            d=d,
            month=month
        )


class UserRelation(Document):
    user = ReferenceField(User, dbref=False)
    follower = ReferenceField(User, dbref=False)

    date_created = DateTimeField()
    date_updated = DateTimeField()

    def __unicode__(self):
        return '%s followed by %s' % (self.user,self.follower)

    def save(self, *args, **kargs):
        self.date_updated = datetime.utcnow()
        if not self.date_created:
            self.date_created = self.date_updated
        super(UserRelation, self).save(*args, **kargs)

class UserCommentVotes(Document):
    user = ReferenceField(User, dbref=False)
    comment = ReferenceField(Comment, dbref=False)
    value = IntField(default=0)

    date_created = DateTimeField()
    date_updated = DateTimeField()

    def save(self, *args, **kargs):
        self.date_updated = datetime.utcnow()
        if not self.date_created:
            self.date_created = self.date_updated
        super(UserCommentVotes, self).save(*args, **kargs)


class ScheduledPost(Document):
    user = ReferenceField(User, reverse_delete_rule=CASCADE, dbref=False)
    post = ReferenceField(Post, dbref=False)
    scheduled_datetime = DateTimeField()
    submitted = BooleanField(default=False)
    service_alias = StringField()


class TrendingTopic(Document):
    topic = StringField()
    date_created = DateTimeField()
    date_updated = DateTimeField()

    def save(self, *args, **kargs):
        self.date_updated = datetime.utcnow()
        if not self.date_created:
            self.date_created = self.date_updated
        super(TrendingTopic, self).save(*args, **kargs)


class Page(Document):
    title = StringField()
    content = StringField()
    slug = StringField()

    date_created = DateTimeField()
    date_updated = DateTimeField()

    meta = {
        'ordering': ['date_created'],
    }

    def __unicode__(self):
        return self.title

    def save(self, *args, **kargs):
        self.date_updated = datetime.utcnow()
        if not self.date_created:
            self.date_created = self.date_updated
        super(Page, self).save(*args, **kargs)


class ErrorLog(Document):
    error = StringField()
    message = StringField()
    data = DictField()

    date_created = DateTimeField()
    date_updated = DateTimeField()

    def save(self, *args, **kargs):
        self.date_updated = datetime.utcnow()
        if not self.date_created:
            self.date_created = self.date_updated
        super(ErrorLog, self).save(*args, **kargs)
