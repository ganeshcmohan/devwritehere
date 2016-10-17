from flask import Blueprint, request, redirect
from flask import url_for, render_template, flash, abort, jsonify
from flask.ext.login import login_required, current_user

from ..forms import PostForm, CommentForm, UploadForm, CropForm, ReplyForm
from ..models import Post, Topic, User, Comment, Reply
from ..settings import PAGINATE
from ..util import html_to_text, nl2brnl, get_user_object
from ..util import extract_chars, split_first_name, clean_breaks
from app.tasks import schedule_post
from urlparse import urlparse
import urllib
from datetime import datetime
from ..tasks import addthis_share_update_for
from six.moves import html_parser

from bson.objectid import ObjectId, InvalidId
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

h = html_parser.HTMLParser()

write = Blueprint('write', __name__, template_folder='../templates')

""" write an opinion """
@write.route('/write', methods=['GET', 'POST'])
@write.route('/write/<post_id>', methods=['GET', 'POST'])
@login_required
def write_opinion(post_id=None):
    user = get_user_object(current_user)
    if not user.verified:
        return redirect(url_for('account.email'))

    form = PostForm()
    upload_form = UploadForm()
    crop_form = CropForm()

    if form.validate_on_submit() and user is not None:
        content = form.content.data
        headline = form.headline.data
        extract = form.extract.data
        photo_source = form.photo_source.data

        twitter_post = form.twitter_post.data
        facebook_post = form.facebook_post.data
        linkedin_post = form.linkedin_post.data


        save_draft = True if form.save_draft.data == 'true' else False

        content = clean_breaks(content).replace("&nbsp", ' ')
        extract = clean_breaks(extract)
        post = Post(
            content = content,
            headline = headline,
            user = user,
            extract = extract,
            is_draft = save_draft,
        )

        post.twitter_post = twitter_post
        post.facebook_post = facebook_post
        post.linkedin_post = linkedin_post

        # create or get topics
        topics = request.form.getlist('topics')
        for topic_id in topics:
            topic = Topic.objects.get(id=ObjectId(topic_id))
            post.topics.append(topic)
            topic.posts += 1
            topic.update_timestamp()
            topic.save()

        # save photo if it exists
        if user.crop_photo:
            photo = user.crop_photo
            if photo:
                if post.photo:
                    post.photo.replace(photo, content_type='JPEG')
                else:
                    post.photo.put(photo, content_type='JPEG')
                post.photo_source = photo_source
                post.photo_orientation = user.crop_photo_orientation
                user.crop_photo.delete()
                user.crop_photo_orientation = None
                user.crop_photo = None
                user.save()

        post.create()

        if not user.has_facebook and not user.has_twitter:
            flash("Connect your social accounts", 'no_social')

        if not post.is_draft:
            if facebook_post:
                print 'facebook_post'
                schedule_post('facebook', str(user.id), str(post.id), hour=14)
            if twitter_post:
                print 'twitter_post'
                schedule_post('twitter', str(user.id), str(post.id), hour=13)
            if linkedin_post:
                schedule_post('linkedin', str(user.id), str(post.id), hour=14)

        return redirect(url_for('write.post', date_slug=post.date_slug, post_slug=post.slug))

    topics = []
    if post_id:
        try:
            ref_post = Post.objects(id=ObjectId(post_id)).first()
            topics = ref_post.topics
        except InvalidId:
            pass

    # clear old photos
    user.crop_photo.delete()
    user.crop_photo = None
    user.crop_photo_orientation = None
    user.save()

    pjax = request.headers.get('X-PJAX',False)
    if pjax:
        tmpl = 'post_edit_inc.html'
    else:
        tmpl = 'post_edit.html'

    return render_template(tmpl,
        form=form,
        pjax=pjax,
        upload_form=upload_form,
        crop_form=crop_form,
        user=user,
        topics=topics
    )


""" update an opinion """
@write.route('/update/<opinion_id>', methods=['GET', 'POST'])
@login_required
def update_opinion(opinion_id):
    try:
        post = Post.objects(id=ObjectId(opinion_id)).first()
    except InvalidId:
        # TODO: put proper error page here
        return "404", 404

    user = get_user_object(current_user)

    if not user.is_super:
        if user != post.user:
            # TODO: put proper error page here
            return "403", 403

    form = PostForm()
    upload_form = UploadForm()
    crop_form = CropForm()

    if form.validate_on_submit() and user is not None:
        content = form.content.data
        headline = form.headline.data
        extract = form.extract.data
        photo_source = form.photo_source.data

        save_draft = True if form.save_draft.data == 'true' else False

        content = clean_breaks(content).replace("&nbsp", ' ')
        extract = clean_breaks(extract)

        twitter_post = form.twitter_post.data
        facebook_post = form.facebook_post.data
        linkedin_post = form.linkedin_post.data

        changed = False

        if post.content.strip() != content.strip():
            post.content = content
            changed = True
        if post.headline.strip() != headline.strip():
            post.headline = headline
            changed = True
        if post.extract.strip() != extract.strip():
            post.extract = extract
            changed = True

        # create or get topics
        for topic in post.topics:
            topic.posts -= 1
            topic.save()
        post.topics = []

        topics = request.form.getlist('topics')
        for topic_id in topics:
            topic = Topic.objects.get(id=ObjectId(topic_id))
            post.topics.append(topic)
            topic.posts += 1
            topic.update_timestamp()
            topic.save()

        # save photo if it exists
        post.photo_source = photo_source
        if user.crop_photo:
            photo = user.crop_photo
            if photo:
                if post.photo:
                    post.photo.replace(photo, content_type='JPEG')
                else:
                    post.photo.put(photo, content_type='JPEG')

                post.photo_orientation = user.crop_photo_orientation
                user.crop_photo.delete()
                user.crop_photo_orientation = None
                user.crop_photo = None

                user.save()

        if form.delete_photo.data == 'true':
            post.photo.delete()
            post.photo = None
            post.photo_orientation = None
            post.photo_source = None

        comments = Comment.objects(post=post.id)
        for comment in comments:
            #comment.extract = comment.extract.strip('<br>').strip()
	    comment.extract = comment.extract.strip('<br>').strip()
            comment.has_changed = comment.extract not in  h.unescape(post.content).strip('<br>').strip()
	    comment.save()

        if post.is_draft and form.save_draft.data != 'true':
            if facebook_post:
                schedule_post('facebook', str(user.id), str(post.id), hour=14)
            if twitter_post:
                schedule_post('twitter', str(user.id), str(post.id), hour=13)
            if linkedin_post:
                schedule_post('linkedin', str(user.id), str(post.id), hour=14)
            post.is_draft = False
        else:
            post.is_draft = save_draft

        post.facebook_post = facebook_post
        post.twitter_post = twitter_post
        post.linkedin_post = linkedin_post

        if changed:
            post.save()
        else:
            post.silent_save()

        flash('Successfully updated opinion!', 'success')
        return redirect(url_for('write.post', date_slug=post.date_slug, post_slug=post.slug))

    form.content.data = post.content
    form.headline.data = post.headline
    form.topics.data = [str(t.id) for t in post.topics]
    form.extract.data = html_to_text(extract_chars(post.extract, 150))
    form.photo_source.data = post.photo_source

    return render_template('post_edit.html',
        form=form,
        upload_form=upload_form,
        crop_form=crop_form,
        user=user,
        post=post
    )

""" delete 'opinion """
@write.route('/delete/<opinion_id>')
@login_required
def delete_opinion(opinion_id):
    user = get_user_object(current_user)

    """ validate opinion and user """
    try:
        post = Post.objects(id=ObjectId(opinion_id)).first()
    except InvalidId:
        # TODO: put proper error page here
        return "404", 404

    if user != post.user:
        # TODO: put proper error page here
        return "403", 403

    old_topics = post.topics
    post.delete()
    for topic in old_topics:
        last_opinion = Post.objects(topics=topic).order_by('-date_updated').first()
        if last_opinion:
            topic.date_update = last_opinion.date_updated
            topic.date_updated_timestamp = last_opinion.date_updated_timestamp
            topic.comments -= post.comments
        else:
            topic.comments = 0
        topic.save()

    return redirect(url_for('write.my_page', date_slug=user.date_slug, display_name_slug=user.display_name_slug))

@write.route('/followers/<date_slug>/<display_name_slug>')
def followers(date_slug, display_name_slug):
    this_user = User.objects.get(date_slug=date_slug)
    objs = this_user.followers()
    user = get_user_object(current_user)
    if this_user == user:
        this_user.last_click_followers = datetime.utcnow()
        this_user.save()
    return render_template('writers.html',
        this_user=this_user,
        user=user,
        objs=objs,
        is_following=user.is_following(this_user.id),
        active_followers = 'active',
    )

@write.route('/following/<date_slug>/<display_name_slug>')
def following(date_slug, display_name_slug):
    this_user = User.objects.get(date_slug=date_slug)
    objs = this_user.following()
    user = get_user_object(current_user)
    return render_template('writers.html',
        this_user=this_user,
        user=user,
        objs=objs,
        is_following=user.is_following(this_user.id),
        active_following = 'active',
    )

""" show a user's my page """
@write.route('/my-page/<date_slug>/<display_name_slug>')
def my_page(date_slug, display_name_slug):
    try:
        this_user = User.objects(date_slug=date_slug).first()
        user = get_user_object(current_user)
        if this_user == user:
            posts = Post.objects(user=this_user)
            user.last_click_comments = datetime.utcnow()
            user.save()
        else:
            posts = Post.objects(user=this_user, is_spam__ne=True, is_draft__ne=True)
    except:
        try:
            this_user = User.objects(id=ObjectId(date_slug)).first()
            user = get_user_object(current_user)
            if this_user == user:
                posts = Post.objects(user=this_user)
            else:
                posts = Post.objects(user=this_user, is_spam__ne=True, is_draft__ne=True)
        except:
            return abort(404)

    if not user: return abort(404)

    return render_template('my_page.html',
        this_user=this_user,
        user=user,
        posts=posts,
        is_following=user.is_following(this_user.id),
        active_opinions = 'active',
    )

@write.route('/json/my-page/grid')
def json_my_page_grid():
    sort = request.args.get('sort', False)
    limit = PAGINATE
    page = int(request.args.get('skip', 0))
    user_id = request.args.get('id', False)

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

    if user_id:
        if user_id == str(current_user.id):
            posts = Post.objects(user=ObjectId(user_id))\
            .order_by(order_by)\
            .limit(limit)\
            .skip(page*limit)
        else:
            posts = Post.objects(user=ObjectId(user_id), is_spam__ne=True, is_draft__ne=True)\
            .order_by(order_by)\
            .limit(limit)\
            .skip(page*limit)
    else:
        posts = []

    post_list = []
    for post in posts:
        topics = [
            {'name': topic.topic, 'url': url_for('show_topic', slug=topic.slug)} for topic in post.topics
        ]
        post_json = {
            'opinion_url': post.url,
            'photo_orientation': post.photo_orientation,
            'photo_url': post.photo_url,
            'user_id': str(post.user.id),
            'opinion_id': str(post.id),
            'headline': post.headline,
            'opinion_my_page':post.user.my_page_anchor,
            'opinion_my_page_anchor': post.user.my_page_anchor,
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



""" show a post/opinion """
@write.route('/post/<date_slug>/<post_slug>')
def post(date_slug, post_slug):
    try:
        post = Post.objects(date_slug=date_slug).first()
        if not post:
            return abort(404)

        post.views += 1
        post.silent_save()
        if post.views % 10 == 0:
            addthis_share_update_for.delay(post.id)

        user = get_user_object(current_user)
        valid_comments = Comment.objects(post=post, is_spam=False)
        comments = valid_comments.filter(post=post, has_changed=False).order_by('date_created')
        changed_comments = valid_comments.filter(post=post, has_changed=True)
    except:
        # catch old style urls and do perm redirect
        try:
            post_id = date_slug
            post = Post.objects(id=ObjectId(post_id)).first()
            return redirect('/post/%(date_slug)s/%(post_slug)s' % {
                'date_slug': post.date_slug,
                'post_slug': post.slug
            }, 301)
        except:
            return abort(404)

    # schedule topic update
    post.update_topics()

    popular_topic = None
    search_query = None
    query = None
    try:
        ref = urlparse(str(request.referrer))
        if ref:
            path = ref.path
            if str(path).startswith('/search'):
                _,query = ref.query.split('=')
                search_query = urllib.unquote_plus(query)
            if str(path).startswith('/topic'):
                topic_slug = str(path).split('/')[-1]
                popular_topic = Topic.objects(slug=topic_slug).first()
    except:
        popular_topic = post.popular_topic


    if not popular_topic:
        popular_topic = post.popular_topic

    pjax = request.headers.get('X-PJAX',False)
    if pjax:
        tmpl = 'post_inc.html'
    else:
        tmpl = 'post.html'

    posts = post.related_posts()
    posts_count = posts.count()

    return render_template(tmpl,
        user = user,
        this_user = post.user,
        post = post,
        pjax = pjax,
        posts =  posts,
        posts_count =  posts_count,
        comments = comments,
        changed_comments = changed_comments,
        popular_topic = popular_topic,
        search_query = search_query,
        raw_query = query
    )

@write.route('/comment-delete/<comment_id>')
@login_required
def delete_comment(comment_id):
    comment = Comment.objects(id=ObjectId(comment_id)).first()
    if current_user == comment.user:
        comment.delete()
        return redirect(request.referrer)
    else:
        return redirect(request.referrer)

@write.route('/comment/<post_id>', methods=['GET', 'POST'])
@login_required
def comment(post_id):
    form = CommentForm()
    user = get_user_object(current_user)
    post = Post.objects(id=ObjectId(post_id)).first()

    if not post:
        return ''

    if form.extract.data and form.comment.data:
        if request.method == 'POST':
            comment = Comment(user=user, post=post)
            comment.extract = form.extract.data.strip()
            comment.comment = nl2brnl(form.comment.data.strip())
            comment.date_created = datetime.utcnow()
            comment.save()
            comment.post.save()

            for topic in post.topics:
                topic.comments += 1
                #topic.update_timestamps()
                topic.save()

            return jsonify({
                'result': True,
                'message' : "Added new comment",
                'display_name': user.profile.display_name,
                'first_name': split_first_name(user.profile.display_name),
                'id': str(comment.id),
                'user_my_page_url': user.my_page_url,
                'extract': comment.extract,
                'comment': comment.comment,
                'location': comment.user.profile.location,
                'display_date': comment.display_date,
                'thumb_count': comment.thumb_count,

            })

    return render_template('fragments/comment_form.html',
        user = user,
        post = post,
        form = form,
    )

@write.route('/reply/<comment_id>', methods=['GET', 'POST'])
@login_required
def reply(comment_id):

    form = ReplyForm()
    user = get_user_object(current_user)
    comment = Comment.objects(id=ObjectId(comment_id)).first()

    print user,""

    if not comment:
        return ''

    if form.reply.data:
        if request.method == 'POST':
            reply = Reply(user=user, comment=comment)
            reply.reply = nl2brnl(form.reply.data.strip())
            reply.date_created = datetime.utcnow()
            reply.save()
            reply.comment.save()

            
            return jsonify({
                'result': True,
                'message' : "Added new reply",
                'display_name': user.profile.display_name,
                'first_name': split_first_name(user.profile.display_name),
                'id': str(reply.id),
                'user_my_page_url': user.my_page_url,
                'reply': reply.reply,
                'location': reply.user.profile.location,
                'display_date': reply.display_date,
                'user_image_url':user.avatar_url()

            })

    return False


@write.route('/replies/<comment_id>', methods=['GET', 'POST'])
@login_required
def replies(comment_id):

    user = get_user_object(current_user)
    replies = Reply.objects(comment=ObjectId(comment_id)).order_by('date_created')
    # print replies,"----"
    reply_lists = []  
    try:
        print replies,"--------------"
        reply_lists = []
        for reply in replies:
            reply_list = {}
            reply_list['author'] = reply.user.profile.display_name
            reply_list['author_avatar'] = reply.user.avatar_url()
            reply_list['author_page_url'] = reply.user.my_page_url
            reply_list['reply'] = reply.reply
            print "replylist..",reply_lists
            reply_lists.append(reply_list)

    except Exception as exc:
        print exc
    if replies:    
        return jsonify({
            'result': reply_lists      
        })
    else:       
        return jsonify({
                'result': False      
            })

