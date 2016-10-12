from models import Post, Comment, SocialConnection, User, ScheduledPost, TrendingTopic, ErrorLog, Topic
from mongoengine import connect
from bson.objectid import ObjectId, InvalidId
from celery import Celery
from settings import OAUTH_TWITTER, OAUTH_LINKEDIN, HTTP_EXTERNAL_BASE, ADDTHIS_SHARES_URL, LONG_URL_OPINION, \
    SHORT_URL_OPINION
from util import next_weekday, html_to_text
from xml.dom import minidom
import oauth2 as oauth
from linkedin import LinkedinAPI
import facebook as fb
import twitter as tw
import datetime
import urllib2
import re

from settings import MONGODB_DB, MONGODB_HOST, FACEBOOK_SDK_VERSION
app = Celery()
connect(MONGODB_DB, host=MONGODB_HOST)

""" utility functions """

def log_error(error, message, data):
    try:
        log = ErrorLog()
        log.error = error
        log.message = message
        log.data = data
    except:
        pass
    finally:
        log.save()


def schedule_post(alias, user_id, post_id, hour=14):
    try:
        if alias == 'facebook':
            fb_post_opinion.apply_async([str(user_id), str(post_id)])
        elif alias == 'twitter':
            tw_post_opinion.apply_async([str(user_id), str(post_id)])
        elif alias == 'linkedin':
            li_post_opinion.apply_async([str(user_id), str(post_id)])
        else:
            return False

        post = Post.objects(id=ObjectId(post_id)).first()
        user = User.objects(id=ObjectId(user_id)).first()

        scheduled = ScheduledPost()
        scheduled.service_alias = alias
        scheduled.post = post
        scheduled.user = user
        scheduled.save()
    except Exception, e:
        print 'schedule_post',e
        pass

    return True
    """
    #try:
    post = Post.objects(id=ObjectId(post_id)).first()
    user = User.objects(id=ObjectId(user_id)).first()



    scheduled = ScheduledPost()
    scheduled.service_alias = alias
    scheduled.post = post
    scheduled.user = user
    scheduled.scheduled_datetime = next_weekday(tz='US/Central', hour=hour)  # 14 == 3pm CST
    scheduled.save()
    #except:
    #    data = {
    #       'post_id': post_id,
    #       'user_id': post_id
    #    }
    #    log_error(alias, 'Failed while attempting to schedule a post to %(alias)s' % {'alias': alias}, data)
    """

def proper_capitalization(s):
    replace_func = lambda m: m.group(1) + m.group(2).upper()
    return re.sub("(^|\s)(\S)", replace_func, str(s))

@app.task
def addthis_share_update_for(post_id):
    post = Post.objects.get(id=ObjectId(post_id))
    post.update_shares()

""" addthis share counts """
@app.task
def addthis_share_update():

    for post in Post.objects.order_by('shares_updated'):
        if post.should_update_shares():
            post.update_shares()

""" trending topics """

@app.task
def update_topic_counts(topic_id):
    topic = Topic.objects(id=ObjectId(topic_id)).first()
    if topic:
        posts = Post.objects(topics=topic.id)
        comment_count = 0
        view_count = 0
        for p in posts:
            comment_count += Comment.objects(post=p.id).count()
            view_count += p.views
        topic.views = view_count
        topic.comments = comment_count
        topic.posts = len(posts)
        topic.save()



""" tasks """

@app.task
def social_post_task():
    to_post = ScheduledPost.objects(scheduled_datetime__lt=datetime.datetime.utcnow(), submitted=False)
    count = 0
    for s in to_post:
        if s.service_alias == 'facebook':
            result = fb_post_opinion(str(s.post.user.id), str(s.post.id))
            count += 1
        if s.service_alias == 'twitter':
            count += 1
            result = tw_post_opinion(str(s.post.user.id), str(s.post.id))
        if s.service_alias == 'linkedin':
            count += 1
            result = li_post_opinion(str(s.post.user.id), str(s.post.id))
        if result:
            s.submitted = True
            s.save()
    return str(count)

@app.task
def fb_post_opinion(user_id, opinion_id):
    """ attempts to post an opinion to user's wall if oauth token is valid """
    print 'fb_post_opinion call'
    try:
        user = User.objects(id=ObjectId(user_id)).first()
        opinion = Post.objects(id=ObjectId(opinion_id)).first()
    except Exception,e:
        print "fb_post_opinion",e
        return False

    if not user or not opinion:
        return False

    count = 0
    connections = SocialConnection.objects(user_id=user.id, service_alias='facebook')
    for con in connections:
        graph = fb.GraphAPI(con.access_token, version=FACEBOOK_SDK_VERSION)

        if opinion.photo:
            photo_url = "http://writehere.com/media/photos/opinion/{opinion_id}".format(opinion_id=str(opinion.id))
        else:
            photo_url = 'http://writehere.com/static/img/wh.jpg'

        message = 'My latest post on WriteHere: {headline} - {short_url}'.format(headline=opinion.headline, short_url=opinion.short_url)

        data = {"name": str(opinion.headline),
                "link": str(opinion.short_url),
                "caption": "",
                "description": "{display_name}: {extract}... at WriteHere.com.".format(
                    display_name=opinion.user.profile.display_name,
                    extract=html_to_text(opinion.extract)

                ),
                "picture": photo_url}

        message = 'My latest post on WriteHere: {headline} - {short_url}'.format(headline=opinion.headline, short_url=opinion.short_url)

        #graph.put_object("me", "feed", message="Testing an automated wall post.")
        graph.put_wall_post(message=message, attachment=data)
        count += 1

    return True

@app.task
def tw_post_opinion(user_id, opinion_id):
    """attempts to post an opinion to the user's twitter """
    print 'tw_post_opinion call'
    try:
        user = User.objects(id=ObjectId(user_id)).first()
        opinion = Post.objects(id=ObjectId(opinion_id)).first()
    except Exception,e:
        print "tw_post_opinion",e
        return False

    if not user or not opinion:
        return False

    message = 'My latest post on WriteHere: {headline} - {short_url}'.format(headline=opinion.headline, short_url=opinion.short_url)

    consumer_key = OAUTH_TWITTER['consumer_key']
    consumer_secret = OAUTH_TWITTER['consumer_secret']
    count = 0
    connections = SocialConnection.objects(user_id=user.id, service_alias='twitter')
    for con in connections:
        count += 1
        api = tw.Api(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token_key=con.access_token,
            access_token_secret=con.secret
        )

        api.PostUpdate(message)

    return True

@app.task
def li_post_opinion(user_id, opinion_id):
    """ post opinion to linkedin if available """

    try:
        user = User.objects(id=ObjectId(user_id)).first()
        opinion = Post.objects(id=ObjectId(opinion_id)).first()
    except:
        return 'exception'

    if not user or not opinion:
        return 'not found'

    #message = 'I just wrote an opinion on WriteHere about %(topic)s. Read it here: %(url)s' % {
    #    'topic': opinion.topics[0].topic,
    #    'url': opinion.short_url
    #}

    consumer_key = OAUTH_LINKEDIN['consumer_key']
    consumer_secret = OAUTH_LINKEDIN['consumer_secret']

    count = 0
    connections = SocialConnection.objects(user_id=user.id, service_alias='linkedin')
    for con in connections:
        count += 1

        api = LinkedinAPI(api_key=consumer_key,
                          api_secret=consumer_secret,
                          oauth_token=con.access_token,
                          oauth_token_secret=con.secret)

        #message = 'I just wrote an opinion on WriteHere about %(topic)s. Read it here: %(url)s' % {
        #    'topic': opinion.topics[0].topic,
        #    'url': opinion.short_url
        #}

        message = 'My latest post on WriteHere: {headline} - {short_url}'.format(headline=opinion.headline, short_url=opinion.short_url)

        share_content = {
            "comment": message,
            "content": {
                "title": str(opinion.headline),
                "submitted-url": str(opinion.short_url),
                "submitted-image-url": "http://writehere.com/static/img/wh.jpg",
                "description": str(html_to_text(opinion.extract))
            },
            "visibility": {
                "code": "anyone"
            }
        }

        return api.post('people/~/shares', params=share_content)

    return str(count)

