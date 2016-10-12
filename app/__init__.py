from markdown import markdown
from slugify import slugify
from flask import Flask, render_template, request, url_for
from flask import  g, session, redirect, jsonify, current_app, make_response
from flask.ext.mongoengine import MongoEngine
from flask.ext.login import current_user, login_required, logout_user
from flask.ext.uploads import UploadSet, configure_uploads
from flask.ext.assets import Environment, Bundle
from flask.ext.security import Security, MongoEngineUserDatastore, LoginForm
from flask.ext.social import login_failed
from flask.ext.social.utils import get_connection_values_from_oauth_response
#from tasks import addthis_share_update
from .util import nl2br, br2nl
from .util import get_user_object, extract_chars, MethodRewriteMiddleware
from .util import split_first_space, formatted_date, space_to_break, html_to_text
from .util import split_first_name, send_mail, nl2brnl, unclean_breaks
from .forms import RegisterForm, ForgotPasswordForm
from .models import Post, Topic, Profile, User, Comment, Role
from .models import AnonymousUser, UserCommentVotes, TrendingTopic, Page
from .settings import FLAG_OPINION_TYPES, FLAG_COMMENT_TYPES, PAGINATE, DEFAULT_MAIL_SENDER

from bson.objectid import ObjectId, InvalidId
import os
import datetime
from . import models as m

os.environ['CELERY_CONFIG_MODULE'] = 'app.settings'
import rawes, pytz
db = MongoEngine()

def create_app():
    from extensions import sql, mail, cache

    app = Flask(__name__)
    app.config.from_object('app.settings')

    # middleware

    db.init_app(app)
    sql.init_app(app)
    mail.init_app(app)
    cache.init_app(app)

    assets = Environment()
    assets.init_app(app)
    app.security = Security(app, MongoEngineUserDatastore(db, User, Role))
    app.db = db
    #app.social = Social(app, MongoEngineConnectionDatastore(db, Connection))
    app.login_manager.anonymous_user = AnonymousUser

    def register_filters():
        import urllib2
        from .util import strip_tags, urlify
        app.jinja_env.filters['slugify'] = slugify
        app.jinja_env.filters['strip_tags'] = strip_tags
        app.jinja_env.filters['decode'] = urllib2.unquote
        app.jinja_env.filters['split_first_space'] = split_first_space
        app.jinja_env.filters['split_first_name'] = split_first_name
        app.jinja_env.filters['space_to_break'] = space_to_break
        app.jinja_env.filters['formatted_date'] = formatted_date
        app.jinja_env.filters['nl2br'] = nl2br
        app.jinja_env.filters['nl2brnl'] = nl2brnl
        app.jinja_env.filters['unclean_breaks'] = unclean_breaks
        app.jinja_env.filters['html_to_text'] = html_to_text
        app.jinja_env.filters['markdown'] = markdown
        app.jinja_env.filters['urlify'] = urlify # override the jinja2 version

    def register_blueprints():
        from .views.account import account
        from .views.media import media
        from .views.search import search
        #from .views.general import general
        from .views.write import write
        from .views.general import general
        from .views.admin import admin

        app.register_blueprint(search)
        app.register_blueprint(account)
        app.register_blueprint(media, url_prefix='/media')
        app.register_blueprint(write)
        app.register_blueprint(general)
        app.register_blueprint(admin)

    register_filters()
    register_blueprints()

    #assets
    #css_base = Bundle(
        #'bootstrap-2.3.2/css/bootstrap.min.css',
        #'css/jquery.tagit.css',
        #'css/main.css',
        #filters=['cssmin'], output='gen/packed.css'
    #)

    css_upload = Bundle(
        'css/jquery-ui.css',
        'css/jquery.imagecrop.css',
        filters=['cssmin'], output='gen/packed_upload.css'
    )

    js_upload = Bundle(
        'js/jquery.imagecrop.min.js',
        filters=['jsmin'], output='gen/packed_upload.js'
    )

    #js_base = Bundle(
        #'js/jquery.bootstrap.js',
        #'js/jquery.bootstrap.typeahead.js',
        #'bootstrap-2.3.2/js/bootstrap.js',
        #'js/jquery.events.js',
        #'js/jquery.easymodal.min.js',
        #'js/jquery.form.js',
        #'js/jquery.highlight.js',
        #'js/jquery.tagit.js',
        #'js/jquery.resize.min.js',
        #'js/jquery.validate.min.js',
        #'js/jquery.easing.js',
        #'js/jquery.mousewheel.min.js',
        #'js/writehere.js',
        #filters=['jsmin'], output='gen/packed.js'
    #)

    #assets.register('js_base', js_base)
    assets.register('js_upload', js_upload)
    #assets.register('css_base', css_base)
    assets.register('css_upload', css_upload)

    # file uploads
    images = UploadSet("images", ('JPG', 'JPEG', 'GIF', 'PNG', 'SVG', 'jpg', 'jpeg', 'gif', 'png', 'svg'))
    configure_uploads(app, images)

    # elastic search
    app.es = rawes.Elastic('localhost:9200')

    # Attach RAuth based login providers
    from .oauth import PROVIDERS
    map(lambda p: p.setup(app), PROVIDERS)

    class SocialLoginError(Exception):
        def __init__(self, provider):
            self.provider = provider

    @app.errorhandler(SocialLoginError)
    def social_login_error(error):
        return redirect(
            url_for('account.register', provider_id=error.provider.id, login_failed=1))

    @login_failed.connect_via(app)
    def on_login_failed(sender, provider, oauth_response):
        app.logger.debug('Social Login Failed via %s; '
                         '&oauth_response=%s' % (provider.name, oauth_response))
        # Save the oauth response in the session so we can make the connection
        # later after the user possibly registers
        session['failed_login_connection'] =\
        get_connection_values_from_oauth_response(provider, oauth_response)
        raise SocialLoginError(provider)

    def after_this_request(func):
        if not hasattr(g, 'call_after_request'):
            g.call_after_request = []
        g.call_after_request.append(func)
        return func


    @app.after_request
    def per_request_callbacks(response):
        for func in getattr(g, 'call_after_request', ()):
            response = func(response)
        return response

    @app.before_request
    def before_request():
        db.connect('writehere')
        g.db = db
        g.user = None

        first_cookie = request.cookies.get('first-visit')
        if first_cookie is None:
            @after_this_request
            def remember_first_visit(response):
                response.set_cookie('first-visit', 'no')
                return response
        g.first_visit = first_cookie is None

        d = datetime.datetime(2000,1,1,0,0,0,0)
        g.topics = m.Topic.objects(date_created__lte=d)

    @app.teardown_request
    def teardown_request(exception):
        if hasattr(g, 'db'):
            # g.db.connection.disconnect()
            pass

    @app.context_processor
    def login_form():
        login_user_form = LoginForm()
        register_user_form = RegisterForm()
        forgot_password_form = ForgotPasswordForm()
        return dict(
            login_user_form=login_user_form,
            register_user_form=register_user_form,
            forgot_password_form=forgot_password_form,
            first_visit=g.first_visit,
        )

    """ end app instantiation """

    # TODO: move these into appropriate blueprints
    @app.route('/')
    def index():
        #try:
            #addthis_share_update.apply_async()
        #except:
            #pass
        user = get_user_object(current_user)
        if not user.is_anonymous:
            if user.requires_refresh:
                user.requires_refresh = False
                user.save()
                logout_user()
                resp = make_response(redirect(url_for('index')))
                return resp

        return render_template('index.html',
            user=user,
            show_filter=True,
            load_url = url_for('index_json_simple'),
        )

    @app.route('/index/json/simple')
    def index_json_simple():
        sort = request.args.get('sort', False)
        writers = request.args.get('writers', False)
        limit = PAGINATE
        page = int(request.args.get('skip', 0))

        if sort == 'latest':
            order_by = '-date_updated_timestamp'
        elif sort == 'opinions':
            order_by = '-posts'
        elif sort == 'shares':
            order_by = '-shares'
        elif sort == 'comments':
            order_by = '-comment_increment'
        elif sort == 'views':
            order_by = '-views'
        else:
            order_by = '-id'

        posts = Post.objects(is_spam__ne=True, is_draft__ne=True)
        if writers == 'followed':
            user = get_user_object(current_user)
            if user.is_authenticated:
                user_relations = m.UserRelation.objects(follower=user)
                users = [ur.user for ur in user_relations]
                posts = posts.filter(user__in=users)
        posts = posts.order_by(order_by).limit(limit).skip(page*limit)

        post_list = []

        for post in posts:

            topics = [{'name': topic.topic, 'url': url_for('show_topic', slug=topic.slug)} for topic in post.topics]

            post_json = {
                'opinion_url': post.url,
                'photo_orientation': post.photo_orientation,
                'photo_url': post.photo_url,
                'user_id': str(post.user.id),
                'opinion_id': str(post.id),
                'headline': post.headline,
                'opinion_my_page':post.user.my_page_anchor,
                'views': post.views,
                'shares': post.shares,
                'comments': post.comments,
                'timestamp': post.timestamp,
                'opinion_update_url' : url_for('write.update_opinion', opinion_id=post.id),
                'opinion_delete_url' : url_for('write.delete_opinion', opinion_id=post.id),
                'opinion_my_page_url': url_for('write.my_page', date_slug=post.user.date_slug, display_name_slug=post.user.display_name_slug),
                'opinion_my_page_anchor': post.user.my_page_anchor,
                'extract': html_to_text(post.extract),
                'opinion_write_url': url_for('write.write_opinion', post_id=post.id),
                'hover_edit' : 'hover-edit' if post.user.id == current_user.id else '',
                'is_spam': 'is-spam' if post.is_spam else '',
                'is_draft': 'is-draft' if post.is_draft else '',
                'topic_list': topics,
                'topic_count': len(topics),
            }
            post_list.append(post_json)

        last_page = len(post_list) < limit

        return jsonify({
            'result': True,
            'opinions': post_list,
            'last_page': last_page
        })

    @app.route('/index/json')
    def index_json():
        last_id = request.args.get('last_id', 0)
        last_page = request.args.get('last_page', 'false')
        topic_id = request.args.get('db_id', False)
        sort = request.args.get('sort', False)
        limit = PAGINATE
        page = request.args.get('page', 1)

        if last_page == 'true':
            topics = []
        else:

            if sort:
                if sort == 'views':
                    sort_by = '-views'
                elif sort == 'opinions':
                    sort_by = '-posts'
                else:
                    sort_by = '-date_updated_timestamp'
            else:
                sort_by = '-date_updated_timestamp'

            if last_id:
                if sort != 'latest':
                    last_topic = Topic.objects(id=ObjectId(last_id)).first()
                    topics = Topic.objects(posts__gt=0).order_by(sort_by).skip
                else:
                    topics = Topic.objects(posts__gt=0, date_updated_timestamp__lte=int(last_id)).order_by(sort_by)
            else:
                topics = Topic.objects(posts__gt=0).order_by(sort_by)

        topic_list = []
        count = 0
        for topic in topics:
            if str(topic.id) == topic_id: continue
            count += 1
            if count > limit: break

            topic_json = {
                'topic': str(topic.topic),
                'opinions': topic.posts,
                'comments': topic.comments,
                'views': topic.views,
                'timestamp': int(topic.date_updated_timestamp),
                'topic_url': url_for('show_topic', slug=topic.slug),
                'topic_photo_url': topic.photo_url,
                'topic_id': str(topic.id),
                'topic_opinion_id': str(topic.post.id),
                'topic_photo_orientation': str(topic.photo_orientation),
                'my_page_url': url_for('write.my_page', date_slug=topic.post.user.date_slug, display_name_slug=topic.post.user.display_name_slug),
                'my_page_anchor': topic.post.user.my_page_anchor,
                'opinion_write_url': url_for('write.write_opinion', post_id=topic.post.id),
                'extract': html_to_text(topic.post.extract),
                'opinion_url': topic.post.url,
                'id': str(topic.id),
            }
            topic_list.append(topic_json)


        if len(topic_list):
            last_topic = topic_list[-1]
            if sort == 'latest':
                last_id =  last_topic['timestamp']
            else:
                last_id = last_topic['id']

            topic_id = last_topic['id']
        else:
            last_id = None

        last_page = len(topic_list) < limit

        return jsonify({
            'result': True,
            'opinions': topic_list,
            'last_id': last_id,
            'last_page': last_page,
            'db_id': topic_id
        })

    @app.route('/topic/<slug>')
    def show_topic(slug=None):
        if not slug:
            redirect(url_for('index'))

        topic = Topic.objects(slug=slug.lower()).first()
        user = get_user_object(current_user)

        if not topic:
            return redirect(url_for('index'))

        #topic.views += 1
        #topic.save()

        posts = Post.objects(topics=topic.id, is_spam__ne=True, is_draft__ne=True)

        return render_template('topic.html',
            topic=topic,
            posts=posts,
            load_url = url_for('json_topic_grid'),
            user=user
        )

    @app.route('/json/topics')
    def json_topics():
        start = request.args.get('start')
        if start:
            topics = Topic.objects(topic__istartswith=start).order_by('-date_updated').limit(50)
            topics = set([topic.topic for topic in topics])
            trends = TrendingTopic.objects(topic__istartswith=start).order_by('-date_updated').limit(50)
            trends = set([trend.topic for trend in trends])
            topics |= trends
        else:
            topics = Topic.objects.order_by('-date_updated').limit(50)
            topics = set([topic.topic for topic in topics])
            trends = TrendingTopic.objects.order_by('-date_updated').limit(50)
            trends = set([trend.topic for trend in trends])
            topics |= trends

        topic_list = list(topics)
        return jsonify({'topics': topic_list})

    @app.route('/json/topic/grid')
    def json_topic_grid():
        sort = request.args.get('sort', False)
        writers = request.args.get('writers', False)
        limit = PAGINATE
        page = int(request.args.get('skip', 0))
        topic_id = request.args.get('id', False)

        if sort == 'latest':
            order_by = '-date_updated_timestamp'
        elif sort == 'opinions':
            order_by = '-posts'
        elif sort == 'comments':
            order_by = '-comment_increment'
        elif sort == 'views':
            order_by = '-views'
        elif sort == 'shares':
            order_by = '-shares'
        else:
            order_by = '-id'

        if topic_id:
            posts = Post.objects(topics=ObjectId(topic_id), is_spam__ne=True, is_draft__ne=True)
            posts = posts.order_by(order_by).limit(limit).skip(page*limit)
        else:
            posts = []
        if writers == 'followed':
            user = get_user_object(current_user)
            if user.is_authenticated:
                user_relations = m.UserRelation.objects(follower=user)
                users = [ur.user for ur in user_relations]
                posts = posts.filter(user__in=users)

        post_list = []
        for post in posts:
            topics = [
                {'name': topic.topic, 'url': url_for('show_topic', slug=topic.slug)}
                for topic in post.topics
            ]
            post_json = {
                'opinion_url': post.url,
                'photo_orientation': post.photo_orientation,
                'photo_url': post.photo_url,
                'user_id': str(post.user.id),
                'opinion_id': str(post.id),
                'headline': post.headline,
                'opinion_my_page':post.user.my_page_anchor,
                #'opinion_my_page_anchor':post.user.my_page_anchor,
                'views': post.views,
                'shares': post.shares,
                'comments': post.comments,
                'timestamp': post.timestamp,
                'opinion_update_url' : url_for('write.update_opinion', opinion_id=post.id),
                'opinion_delete_url' : url_for('write.delete_opinion', opinion_id=post.id),
                'opinion_my_page_url': url_for('write.my_page', date_slug=post.user.date_slug, display_name_slug=post.user.display_name_slug),
                'extract': html_to_text(post.extract),
                'opinion_write_url': url_for('write.write_opinion', post_id=post.id),
                'hover_edit' : 'hover-edit' if post.user.id == current_user.id else '',
                'topic_list': topics,
                'topic_count': len(topics),
                'is_draft': '',
                'is_spam': '',
            }
            post_list.append(post_json)

        last_page = len(post_list) < limit

        return jsonify({
            'result': True,
            'opinions': post_list,
            'last_page': last_page
        })

    @app.route('/json/thumb/comment', methods=['POST'])
    @login_required
    def json_thumb_comment():
        comment_id = request.form.get('comment_id')
        vote = int(request.form.get('vote', 0))
        comment = Comment.objects(id=ObjectId(comment_id)).first()

        if not comment:
            return jsonify({'success': False, 'message': 'Invalid comment'})

        user = get_user_object(current_user)
        new_value = int(comment.thumb_count + vote)
        assert new_value in [1, 0, -1]
        UserCommentVotes.objects(user=user, comment=comment).modify(upsert=True, value=new_value)
        comment.modify(thumb_count=new_value)
        return jsonify({
                'thumb_count': new_value,
                'success': True,
                'message': ''
            })

    @app.route('/json/flag/comment', methods=['POST'])
    def json_flag_comment():
        comment_id = request.form.get('comment_id')
        flag = request.form.get('flag')

        try:
            comment = Comment.objects(id=ObjectId(comment_id)).first()
        except InvalidId:
            comment = None



        if comment and any([True for k, v in FLAG_COMMENT_TYPES if k == flag]):
            if not len(comment.flagged):
                comment.flagged = []
            comment.flagged.append(flag)
            comment.save()

            try:
                user_name = current_user.profile.display_name
            except:
                user_name = 'Anonymous'

            send_mail('email/flagged_comment.html',
                      'Comment flagged as %(flag)s' % {'flag': flag},
                      ["josh@writehere.com", "flag@writehere.com"],
                      sender=DEFAULT_MAIL_SENDER,
                      html=True,
                      context={'comment': comment, 'user': user_name, 'flag': flag}
            )

            #msg = Message("Comment flagged as %s" % str(flag),
            #    sender="admin@writehere.com",
            #    recipients=["josh@writehere.com", "flag@writehere.com"])
            #msg.body = 'Commented flagged as %s.' % flag
            #msg.html = 'Commented flagged as %s.' % flag
            #mail.send(msg)

            return jsonify({'flag': flag, 'success': True})
        else:
            return jsonify({'success': False, 'message': 'Invalid flag type'})

    @app.route('/json/flag/opinion', methods=['POST'])
    def json_flag_opinion():
        post_id = request.form.get('post_id')
        flag = request.form.get('flag')

        try:
            post = Post.objects(id=ObjectId(post_id)).first()
        except InvalidId:
            post = None

        try:
            user_name = current_user.profile.display_name
        except:
            user_name = 'Anonymous'

        if post and any([True for k, v in FLAG_OPINION_TYPES if k == flag]):
            if not len(post.flagged):
                post.flagged = []
            post.flagged.append(flag)
            post.save()

            #msg = Message("Opinion flagged as %s" % str(flag),
            #    sender="admin@writehere.com",
            #    recipients=["josh@writehere.com", "flag@writehere.com"])
            #msg.body = 'Opinion flagged as %s.' % flag
            #msg.html = 'Opinion flagged as %s.' % flag
            #mail.send(msg)
            send_mail('email/flagged_opinion.html',
                      'Opinion flagged as %(flag)s' % {'flag': flag},
                      ["josh@writehere.com", "flag@writehere.com"],
                      sender=DEFAULT_MAIL_SENDER,
                      html=True,
                      context={'post': post, 'user': user_name, 'flag': flag}
            )

            return jsonify({'flag': flag, 'success': True})
        else:
            return jsonify({'success': False, 'message': 'Invalid flag type'})


    @app.route('/json/opinion/<direction>')
    def json_comments(direction):
        opinion_id = request.args.get('opinion_id')
        skip = request.args.get('skip', 0)

        topic_id = request.args.get('topic_id')
        success = False
        opinion_url = ''
        extract = ''
        new_opinion_id = ''
        my_page_url = ''
        my_page_text = ''
        opinion_photo_url = None
        opinion_photo_orientation = None

        try:
            #opinion = Post.objects(id=ObjectId(opinion_id)).first()
            topic = Topic.objects(posts__gt=0, id=ObjectId(topic_id)).first()
            success = True
        except InvalidId:
            pass

        skip = int(skip)

        if success and direction == 'previous':
            skip -= 1
            if skip < 0:
                new_opinion = False
            else:
                #new_opinion = db.writehere.find_one({'opinion_id' : {'$lt': opinion.id}})
                new_opinion = Post.objects(
                    topics=topic.id,
                    is_spam__ne=True,
                    is_draft__ne=True
                ).order_by('-weight', 'id').skip(skip).first()

        if success and direction == 'next':
            skip += 1
            new_opinion = Post.objects(
                topics=topic.id,
                is_spam__ne=True,
                is_draft__ne=True
            ).order_by('-weight', 'id').skip(skip).first()

        if new_opinion:
            success = True
            extract = new_opinion.extract
            new_opinion_id = new_opinion.id
            opinion_url = url_for('write.post', date_slug=new_opinion.date_slug, post_slug=new_opinion.slug)
            my_page_url = url_for('write.my_page', date_slug=new_opinion.user.date_slug, display_name_slug=new_opinion.user.display_name_slug)
            my_page_text = extract_chars(unicode(new_opinion.user.profile.display_name) + ', ' + unicode(new_opinion.user.profile.location or ''), 30)
            opinion_photo_url = new_opinion.photo_url
            opinion_photo_orientation = new_opinion.photo_orientation
        else:
            success = False

        return jsonify({
            'result': success,
            'opinion_url': opinion_url,
            'opinion_photo_url': opinion_photo_url,
            'opinion_photo_orientation': opinion_photo_orientation,
            'my_page_url': my_page_url,
            'my_page_text': my_page_text,
            'extract': extract,
            'new_opinion_id': unicode(new_opinion_id),
            'skip': skip
        })

    @app.route('/tasks/update-users')
    @login_required
    def update_users():
        users = User.objects.all()
        for user in users:
            #user.active = True
            #user.roles = []
            #user.password = encrypt_password('password')
            if user.date_created.isoformat() == '2013-03-15T12:49:09.453Z':
                user.date_created = user.date_updated
            user.save()
        return "Done"

    @app.route('/tasks/migrate-dbref')
    def migrate_dbref():
        from .models import UserRelation, ScheduledPost

        for u in User.objects():
            u.roles = u.roles
            u.save()

        for p in Profile.objects():
            p.user = p.user
            p.save()

        for p in Post.objects():
            p.user = p.user
            p.topics = p.topics
            p.save()

        for c in Comment.objects():
            c.user = c.user
            c.post = c.post
            c.save()

        for r in UserRelation.objects():
            r.user = r.user
            r.follower = r.follower
            r.save()

        for x in UserCommentVotes.objects():
            x.user = x.user
            x.comment = x.comment
            x.save()

        for s in ScheduledPost.objects():
            s.user = s.user
            s.post = s.post
            s.save()

        return "Migrated!"

    @app.route('/tasks/update-extracts')
    @login_required
    def update_extracts():
        posts = Post.objects.all()
        for post in posts:
            post.extract = extract_chars(post.content, 150)
            post.save()
        return "Done"

    @app.route('/tasks/update-date')
    @login_required
    def update_date_slug():
        posts = Post.objects.all()
        for post in posts:
            post.create()
        return "Done"

    @app.route('/tasks/user-date')
    def update_user_date_slug():
        users = User.objects.all()
        for u in users:
            u.create()
        return "Done"

    @app.route('/tasks/orphans')
    def clean_orphans():
        comments = Comment.objects.all()
        to_delete = 0
        for comment in comments:
            try:
                user = comment.user.active
            except:
                to_delete += 1
                comment.delete()

        profiles = Profile.objects.all()
        for profile in profiles:
            try:
                user = profile.user.active
            except:
                to_delete += 1
                profile.delete()

        return str(to_delete)

    @app.route('/tasks/update-timestamp')
    @login_required
    def update_timestamp():
        topics = Topic.objects.all()
        for t in topics:
            t.update_timestamp()
            t.save()
        return "done"

    @app.route('/tasks/update-indexes')
    @login_required
    def update_indexes():
        posts = Post.objects.all()
        with current_app.app_context():
            current_app.es.delete('opinions/')

            for post in posts:
                topics = [topic.topic for topic in post.topics]

                current_app.es.put('opinions/opinion/%s' % str(post.id), data= {
                    'post_id': str(post.id),
                    'date_created': post.date_created.replace(tzinfo=pytz.UTC),
                    'content': br2nl(post.content),
                    'headline': br2nl(post.headline),
                    'topics': list(topics),
                    'author_name': str(post.user.profile.display_name),
                    'url': post.url,
                })

            resp = current_app.es.post('opinions', data={
                "mappings":{
                    "opinion":{
                        "properties":{

                            # headline field
                            "headline":{
                                "fields" : {
                                    "partial":{
                                        "search_analyzer":"full_name",
                                        "index_analyzer":"partial_name",
                                        "type":"string"
                                    },
                                    "partial_back":{
                                        "search_analyzer":"full_name",
                                        "index_analyzer":"partial_name_back",
                                        "type":"string"
                                    },
                                    "partial_middle":{
                                        "search_analyzer":"full_name",
                                        "index_analyzer":"partial_middle_name",
                                        "type":"string"
                                    },
                                    "headline":{
                                        "type":"string",
                                        "analyzer":"full_name"
                                    }
                                },
                                "type":"multi_field"
                            },

                            # content field
                            "content":{
                                "fields" : {
                                    "partial":{
                                        "search_analyzer":"full_name",
                                        "index_analyzer":"partial_name",
                                        "type":"string"
                                    },
                                    "partial_back":{
                                        "search_analyzer":"full_name",
                                        "index_analyzer":"partial_name_back",
                                        "type":"string"
                                    },
                                    "partial_middle":{
                                        "search_analyzer":"full_name",
                                        "index_analyzer":"partial_middle_name",
                                        "type":"string"
                                    },
                                    "content":{
                                        "type":"string",
                                        "analyzer":"full_name"
                                    }
                                },
                                "type":"multi_field"
                            },

                            # topics field
                            "topics":{
                                "fields" : {
                                    "partial":{
                                        "search_analyzer":"full_name",
                                        "index_analyzer":"partial_name",
                                        "type":"string"
                                    },
                                    "partial_back":{
                                        "search_analyzer":"full_name",
                                        "index_analyzer":"partial_name_back",
                                        "type":"string"
                                    },
                                    "partial_middle":{
                                        "search_analyzer":"full_name",
                                        "index_analyzer":"partial_middle_name",
                                        "type":"string"
                                    },
                                    "topics":{
                                        "type":"string",
                                        "analyzer":"full_name"
                                    }
                                },
                                "type":"multi_field"
                            },


                            # author_names field
                            "author_name":{
                                "fields" : {
                                    "partial":{
                                        "search_analyzer":"full_name",
                                        "index_analyzer":"partial_name",
                                        "type":"string"
                                    },
                                    "partial_back":{
                                        "search_analyzer":"full_name",
                                        "index_analyzer":"partial_name_back",
                                        "type":"string"
                                    },
                                    "partial_middle":{
                                        "search_analyzer":"full_name",
                                        "index_analyzer":"partial_middle_name",
                                        "type":"string"
                                    },
                                    "author_name":{
                                        "type":"string",
                                        "analyzer":"full_name"
                                    }
                                },
                                "type":"multi_field"
                            },

                            # other fields
                            "date_created":{
                                "type": "date",
                                "index":"analyzed"
                            },
                            "url":{
                                "type": "string",
                                "index":"not_analyzed"
                            },
                            "post_id":{
                                "type": "string",
                                "index":"not_analyzed"
                            },
                            }
                    }
                },
                "settings":{
                    "analysis":{
                        "filter":{
                            "name_ngrams":{
                                "side":"front",
                                "max_gram":50,
                                "min_gram":2,
                                "type":"edgeNGram"
                            },
                            "name_ngrams_back":{
                                "side":"back",
                                "max_gram":50,
                                "min_gram":2,
                                "type":"edgeNGram"
                            },
                            "name_middle_ngrams":{
                                "type":"nGram",
                                "max_gram":50,
                                "min_gram":2
                            }
                        },
                        "analyzer":{
                            "full_name":{
                                "filter":[
                                    "standard",
                                    "lowercase",
                                    "asciifolding"
                                ],
                                "type":"custom",
                                "tokenizer":"standard"
                            },
                            "partial_name":{
                                "filter":[
                                    "standard",
                                    "lowercase",
                                    "asciifolding",
                                    "name_ngrams"
                                ],
                                "type":"custom",
                                "tokenizer":"standard"
                            },
                            "partial_name_back":{
                                "filter":[
                                    "standard",
                                    "lowercase",
                                    "asciifolding",
                                    "name_ngrams_back"
                                ],
                                "type":"custom",
                                "tokenizer":"standard"
                            },
                            "partial_middle_name":{
                                "filter":[
                                    "standard",
                                    "lowercase",
                                    "asciifolding",
                                    "name_middle_ngrams"
                                ],
                                "type":"custom",
                                "tokenizer":"standard"
                            }
                        }
                    }
                }
            })
        return "Done"

    @app.route('/test/search/<keywords>')
    def test_search(keywords):
        data = {
            "query" : {
                "query_string" : {
                    "query" : keywords
                }
            }
        }
        with current_app.app_context():
            rs = current_app.es.get('opinions/opinion/_search', data=data)
        return jsonify(rs)

    app.wsgi_app = MethodRewriteMiddleware(app.wsgi_app)

    return app
