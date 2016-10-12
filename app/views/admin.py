from flask import Blueprint, render_template, request, abort
from flask import jsonify, redirect, flash, url_for
from flask.ext.login import login_required, current_user
from flask.ext.security.utils import encrypt_password
from flask.ext.security import roles_required

from bson.objectid import ObjectId, InvalidId
from passlib.hash import md5_crypt
from ..models import User, Comment, Post, Topic, SQLMailBox, Page, Profile
from ..forms import AdminUserForm, AdminPostForm, AdminTopicForm, AdminEmailForm, AdminEmailCreateForm, AdminPage
from ..util import br2nl, extract_chars, send_mail
from ..settings import DEFAULT_EMAIL_DOMAIN, DEFAULT_MAIL_SENDER, FLAG_OPINION_TYPES, TOPIC_NEW_DATE
from app.extensions import sql
from app.tasks import fb_post_opinion, tw_post_opinion, li_post_opinion
from ..pager import Pager

import sh, datetime, pytz
from datetime import timedelta
from mongoengine import Q

admin = Blueprint('admin', __name__, template_folder='../templates')

PER_PAGE = 50

@admin.route('/admin/schedule-post')
@roles_required('admin')
def scheduled_post():

    flash('Successfully scheduled post for', 'info')
    return redirect(request.referrer)

@admin.route('/admin/post-social')
@roles_required('super')
def post_social():
    opinion_id = request.args.get('opinion_id')
    user = current_user

    try:
        opinion = Post.objects(id=ObjectId(opinion_id)).first()
        assert(opinion is not None)
    except:
        flash('failed to locate opinion')
        return redirect(request.referrer)

    fb_post_opinion.apply_async(args=[str(user.id), str(opinion.id)])
    tw_post_opinion.apply_async(args=[str(user.id), str(opinion.id)])
    li_post_opinion.apply_async(args=[str(user.id), str(opinion.id)])

    flash('Successfully posted to social networks', 'info')
    return redirect(request.referrer)





@admin.route('/admin')
@roles_required('admin')
def admin_index():
    users, posts, comments = {}, {}, {}
    today = datetime.datetime.utcnow()
    utcnow = today.replace(tzinfo=pytz.utc)

    today_begin = utcnow - timedelta(days=1)
    week_begin = utcnow - timedelta(days=7)
    month_begin = utcnow - timedelta(days=30)

    """ set data for content summary table """
    users['today'] = User.objects(date_created__gte=today_begin).count()
    users['week'] = User.objects(date_created__gte=week_begin).count()
    users['month'] = User.objects(date_created__gte=month_begin).count()
    users['total'] = User.objects.all().count()

    posts['today'] = Post.objects(date_created__gte=today_begin, is_spam=False).count()
    posts['week'] = Post.objects(date_created__gte=week_begin, is_spam=False).count()
    posts['month'] = Post.objects(date_created__gte=month_begin, is_spam=False).count()
    posts['total'] = Post.objects.all().count()

    comments['today'] = Comment.objects(date_created__gte=today_begin, is_spam=False).count()
    comments['week'] = Comment.objects(date_created__gte=week_begin, is_spam=False).count()
    comments['month'] = Comment.objects(date_created__gte=month_begin, is_spam=False).count()
    comments['total'] = Comment.objects.all().count()

    """ set data for flag summary table """
    flag_tuple = FLAG_OPINION_TYPES
    for flag_code, flag_name in flag_tuple:
        posts[flag_code] = Post.objects(flagged=flag_code).count()
        comments[flag_code] = Comment.objects(flagged=flag_code).count()


    return render_template('admin/summary.html', **{
        'users': users,
        'posts': posts,
        'comments': comments,
        'today': str(today.strftime("%Y/%m/%d %I:%M%p")),
        #'tz_code': tz_code,
        'flag_types': flag_tuple
    })


@admin.route('/admin/pages', methods=['GET', 'POST'])
@roles_required('admin')
def admin_pages():
    slug = request.args.get('slug', 'about-writehere')
    page = Page.objects.get(slug=slug)

    form = AdminPage()
    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data
        slug = form.slug.data

        page.title = title
        page.content = content
        page.slug = slug
        page.save()

        return redirect(url_for('admin.admin_pages', slug=slug))

    form.title.data = page.title
    form.content.data = page.content
    form.slug.data = page.slug

    return render_template(
        "admin/pages.html",
        form=form,
        pages=Page.objects.all(),
        current_slug=slug
    )


@admin.route('/admin/email')
@login_required
@roles_required('admin')
def admin_email():

    all_objs = SQLMailBox.query.order_by(SQLMailBox.created.desc())
    page = int(request.args.get('page',1))
    pager = Pager(page, PER_PAGE, all_objs)
    return render_template('admin/email.html',
        pager = pager,
    )

@admin.route('/admin/delete-user/<user_id>')
@login_required
@roles_required('admin')
def admin_delete_user(user_id):
    user = User.objects(id=ObjectId(user_id)).first()
    if user:
        user.delete()
    flash('Deleted user')
    return redirect(url_for('admin.users'))

@admin.route('/admin/email/create', methods=['GET','POST'])
@roles_required('admin')
@login_required
def admin_email_create():
    form = AdminEmailCreateForm()
    if form.is_submitted():
        if form.validate():
            alias = form.alias.data.lower()
            username = alias + '@' + DEFAULT_EMAIL_DOMAIN
            maildir = username + '/'
            full_name = form.name.data
            email = SQLMailBox(
                username=username,
                name=full_name,
                maildir=maildir,
                local_part=alias,
                domain=DEFAULT_EMAIL_DOMAIN
            )
            email.name = form.name.data
            email.password = md5_crypt.encrypt(form.password.data)

            try:
                # create mailbox folders on disk
                with sh.sudo:
                    mail_admin = sh.Command('/usr/local/bin/mailbox-admin.py')
                    mail_admin(str(alias), '--create')
                # add mailbox to sql
                sql.session.add(email)
                sql.session.commit()

                # send a welcome e-mail from admin which will activate the box
                send_mail('email/pop3_welcome.html', 'Your new WriteHere e-mail account...', [username], sender=DEFAULT_MAIL_SENDER, html=True, context={})

                return jsonify({'result': True, 'message': 'Saved email information'})
            except:
                return jsonify({'result': False, 'message': 'Unknown error, please try again.'})
        else:
            #errors = form.errors
            #todo: add more validation here
            return jsonify({'result': False, 'message': 'Unknown error, please try again.'})

    return render_template('admin/email_create_form.html',
        form=form
    )

@admin.route('/admin/email/edit', methods=['GET','POST'])
@roles_required('admin')
@login_required
def admin_email_edit():
    username = request.args.get('username', None)
    form = AdminEmailForm()

    try:
        email = SQLMailBox.query.filter_by(username=username).first()
    except InvalidId:
        return abort(404)

    if form.validate_on_submit() and current_user is not None:

        email.name = form.name.data
        if form.password.data != '':
            email.password = md5_crypt.encrypt(form.password.data)
        sql.session.add(email)
        sql.session.commit()
        return jsonify({'result': True, 'message': 'Saved email information'})

    form.name.data = email.name

    return render_template('admin/email_edit_form.html',
        email=email,
        form=form
    )


@admin.route('/admin/email/delete', methods=['GET','POST'])
@roles_required('super')
@login_required
def admin_email_delete():
    username = request.args.get('username', None)

    try:
        email = SQLMailBox.query.filter_by(username=username).first()
    except InvalidId:
        return abort(404)

    # create mailbox folders on disk
    with sh.sudo:
        mail_admin = sh.Command('/usr/local/bin/mailbox-admin.py')
        mail_admin(str(email.local_part), '--delete')

    sql.session.delete(email)
    sql.session.commit()

    return redirect(url_for('admin.admin_email'))

@admin.route('/admin/test2')
def admin_test_2():
    import sh
    with sh.sudo:
        mail_admin = sh.Command('/usr/local/bin/mailbox-admin.py')
        mail_admin('test5', '--create')
    return 'Did it'

@admin.route('/admin/test3')
def admin_test_3():
    import sh
    with sh.sudo:
        mail_admin = sh.Command('/usr/local/bin/mailbox-admin.py')
        mail_admin('test5', '--delete')
    return 'Did it'

@admin.route('/admin/test')
def admin_test_sh():
    """hash = md5_crypt.encrypt('test')
    from sh import chgrp, chown, chmod, maildirmake, sudo
    with sudo:
        maildirmake('/var/vmail/writehere.com/test3')
        chgrp('mail', '-R', '/var/vmail/writehere.com/test3')
        chown('vmail', '-R', '/var/vmail/writehere.com/test3')
        chmod('u+rwx',  '-R', '/var/vmail/writehere.com/test3')

    msg = Message("Hello",
        sender="server@writehere.com",
        recipients=["joshua.purvis@gmail.com"])

    msg.body = 'testing'
    msg.html = '<b>testing</b>'
    with current_app.app_context():
        current_app.mail.send(msg)"""

    return 'Done'

@admin.route('/admin/topics')
@roles_required('admin')
def topics():
    all_objs = Topic.objects.all()
    page = int(request.args.get('page',1))
    q = request.args.get('q','').strip()
    if q:
        q1 = Q(topic__icontains=q)
        all_objs = all_objs.filter(q1)
    pager = Pager(page, PER_PAGE, all_objs, q=q)
    return render_template('admin/topics.html',
        pager = pager,
    )

@admin.route('/admin/topics/form', methods=['GET', 'POST'])
@roles_required('admin')
def topics_form():
    topic_id = request.args.get('topic_id', None)
    form = AdminTopicForm()

    try:
        topic = Topic.objects(id=ObjectId(topic_id)).first()
    except InvalidId:
        return abort(404)

    if form.validate_on_submit() and current_user is not None:
        new_topic = form.topic.data
        existing = Topic.objects(topic=new_topic).first()
        if existing and new_topic != topic.topic:
            return jsonify({'success': False, 'result': False, 'message': 'That topic already exists.', 'reason':'existing'})
        else:
            topic.topic = new_topic
            as_new = form.as_new.data
            if as_new:
                topic.date_created = TOPIC_NEW_DATE
            else:
                if topic.is_new():
                    topic.date_created = datetime.datetime.utcnow()
            topic.save()
            return jsonify({'result': True, 'message': 'Saved user information'})

    form.topic.data = topic.topic
    form.as_new.data = topic.is_new()

    return render_template('admin/topics_form.html',
        topic=topic,
        form=form
    )


@admin.route('/admin/delete/topic/<topic_id>')
@roles_required('admin')
def delete_topic(topic_id):
    topic = Topic.objects(id=ObjectId(topic_id)).first()

    opinions = Post.objects(topics=topic).count()
    if opinions > 0:
        flash("Can't delete topic. Still associated with live opinions.", 'error')
        return redirect(request.referrer)

    topic.delete()

    return redirect(request.referrer)


@admin.route('/admin/users')
@roles_required('admin')
def users():
    all_objs = User.objects.all()
    page = int(request.args.get('page',1))
    q = request.args.get('q','').strip()
    if q:
        q1 = Q(email__icontains=q)
        q2 = Q(username__icontains=q)
        profiles = Profile.objects.filter(display_name__icontains=q)
        emails = [p.user.email for p in profiles]
        q3 = Q(email__in=emails)  # shit
        all_objs = all_objs.filter(q1|q2|q3)
    pager = Pager(page, PER_PAGE, all_objs, q)
    return render_template('admin/users.html',
        pager = pager,
    )

@admin.route('/admin/users/form', methods=['GET','POST'])
@roles_required('admin')
def users_form():
    user_id = request.args.get('user_id', None)
    form = AdminUserForm()

    try:
        user = User.objects(id=ObjectId(user_id)).first()
    except InvalidId:
        return abort(404)

    if form.validate_on_submit() and user is not None:
        password = form.password.data

        if password and password != '':
            user.password = encrypt_password(password)
        user.verified = form.verified.data
        user.email = form.email.data
        user.save()

        profile = user.profile
        profile.display_name = form.display_name.data
        profile.web_presence = form.web_presence.data
        profile.bio = form.bio.data
        profile.location = form.location.data
        profile.save()

        return jsonify({'result': True, 'message': 'Saved user information'})

    form.display_name.data = user.profile.display_name
    form.web_presence.data = user.profile.web_presence
    form.bio.data = user.profile.bio
    form.location.data = user.profile.location
    form.display_name.data = user.profile.display_name
    form.verified.data = user.verified
    form.email.data = user.email

    return render_template('admin/users_form.html',
        user=user,
        form=form
    )

@admin.route('/admin/opinions')
@roles_required('admin')
def opinions():
    user_id = request.args.get('user_id', '')
    topic_id = request.args.get('topic_id', None)
    flag = request.args.get('flag', None)

    if user_id:
        filter_type = 'user'
        filtered = User.objects(id=ObjectId(user_id)).first()
        opinions = Post.objects(user=filtered)
    elif topic_id:
        filter_type = 'topic'
        filtered = Topic.objects(id=ObjectId(topic_id)).first()
        opinions = Post.objects(topics=filtered)
    elif flag:
        filter_type = 'flag'
        flag_type = flag
        filtered = None
        opinions = Post.objects(flagged=flag_type)
    else:
        filter_type = 'all'
        filtered = None
        opinions = Post.objects.all()

    all_objs = opinions
    page = int(request.args.get('page',1))
    q = request.args.get('q','').strip()
    if q:
        q1 = Q(headline__icontains=q)
        users = User.objects.filter(email__icontains=q)
        q2 = Q(user__in=users)
        all_objs = all_objs.filter(q1|q2)
    pager = Pager(page, PER_PAGE, all_objs, q=q, user_id=user_id)

    return render_template('admin/opinions.html',
        pager = pager,
        filtered = filtered,
        filter_type = filter_type,
        flag_type = flag
    )

@admin.route('/admin/opinions/form', methods=['GET','POST'])
@roles_required('admin')
def opinions_form():
    opinion_id = request.args.get('opinion_id', None)
    form = AdminPostForm()

    try:
        opinion = Post.objects(id=ObjectId(opinion_id)).first()
    except InvalidId:
        return abort(404)

    if form.validate_on_submit() and opinion is not None:
        content = form.content.data.strip()
        headline = form.headline.data.strip()
        extract = form.extract.data.strip()

        #content = clean_breaks(content)
        #extract = clean_breaks(extract)

        opinion.content = content
        opinion.headline = headline
        opinion.extract = extract

        # create or get topics
        for topic in opinion.topics:
            topic.posts -= 1
            topic.save()
        opinion.topics = []

        topics = request.form.getlist('topics')
        for topic in topics:
            obj = Topic.objects.get(id=ObjectId(topic))
            opinion.topics.append(obj)
            obj.posts += 1
            obj.save()

        opinion.silent_save()

        comments = Comment.objects(post=opinion.id)
        for comment in comments:
            comment.has_changed = comment.extract not in opinion.content
            comment.silent_save()

        return jsonify({'result': True, 'message': 'Saved opinion information'})

    form.content.data = br2nl(opinion.content)
    form.headline.data = str(opinion.headline)
    form.extract.data = br2nl(extract_chars(opinion.extract, 150))
    form.is_spam.data = opinion.is_spam
    form.topics.data = [str(t.id) for t in opinion.topics]

    return render_template('admin/opinions_form.html',
        opinion=opinion,
        form=form
    )

@admin.route('/admin/weight/opinion', methods=['POST'])
@roles_required('admin')
def opinion_update_weight():
    opinion_id = request.form.get('opinion_id')
    weight = request.form.get('weight')

    if not weight or not opinion_id: return jsonify({'result': False})

    try:
        opinion = Post.objects(id=ObjectId(opinion_id)).first()
        opinion.weight = int(weight)
        opinion.save()
    except:
        return jsonify({'result': False, 'message': 'Weight must be a number'})

    return jsonify({'result': True})

""" flag classification """

@admin.route('/admin/unflag/opinion/<opinion_id>/<flag_type>')
@roles_required('admin')
def delete_flag(opinion_id, flag_type):
    opinion = Post.objects(id=ObjectId(opinion_id)).first()
    opinion.flagged = filter(lambda x: x != flag_type, opinion.flagged)
    opinion.silent_save()
    return redirect(request.referrer)

@admin.route('/admin/unflag/comment/<comment_id>/<flag_type>')
@roles_required('admin')
def delete_flag_comment(comment_id, flag_type):
    comment = Comment.objects(id=ObjectId(comment_id)).first()
    comment.flagged = filter(lambda x: x != flag_type, comment.flagged)
    comment.save()
    return redirect(request.referrer)

@admin.route('/admin/delete/opinion/<opinion_id>')
@roles_required('admin')
def delete_opinion(opinion_id):
    opinion = Post.objects(id=ObjectId(opinion_id)).first()

    old_topics = opinion.topics
    opinion.delete()
    for topic in old_topics:
        last_opinion = Post.objects(topics=topic).order_by('-date_updated').first()
        if last_opinion:
            topic.date_update = last_opinion.date_updated
            topic.date_updated_timestamp = last_opinion.date_updated_timestamp
            topic.comments -= opinion.comments
        else:
            topic.comments = 0
        topic.save()


    return redirect(request.referrer)

@admin.route('/admin/spam/opinion', methods=['POST'])
@roles_required('admin')
@login_required
def spam_mark_opinion():
    toggle = int(request.form.get('toggle', 1))
    opinion_id = request.form.get('opinion_id', None)

    if not opinion_id:
        return jsonify({'result': False, 'message': 'Invalid opinion Id'})

    opinion = Post.objects(id=ObjectId(opinion_id)).first()
    if not opinion:
        return jsonify({'result': False, 'message': 'Invalid opinion Id'})

    is_spam = True if toggle else False
    opinion.set_spam(is_spam)

    return jsonify({'result': True, 'message': 'Set spam marker'})

""" mark comment as spam via GET confirmation method """
@admin.route('/admin/spam/comment/<comment_id>', methods=['GET'])
@roles_required('admin')
@login_required
def spam_flag_comment(comment_id):
    comment = Comment.objects(id=ObjectId(comment_id)).first()
    if comment:
        is_spam = False if comment.is_spam else True
        comment.set_spam(is_spam)
    return redirect(request.referrer)

""" mark opinion as spam via GET confirmation method """
@admin.route('/admin/spam/opinion/<opinion_id>', methods=['GET'])
@roles_required('admin')
@login_required
def spam_flag_opinion(opinion_id):
    opinion = Post.objects(id=ObjectId(opinion_id)).first()
    if opinion:
        is_spam = False if opinion.is_spam else True
        opinion.set_spam(is_spam)
    return redirect(request.referrer)

@admin.route('/admin/comments')
@roles_required('admin')
def comments():
    opinion_id = request.args.get('opinion_id', None)
    topic_id = request.args.get('topic_id', None)
    user_id = request.args.get('user_id', None)
    flag = request.args.get('flag', None)

    if opinion_id:
        filter_type = 'opinion'
        filtered = Post.objects(id=ObjectId(opinion_id)).first()
        comments = Comment.objects(post=filtered)
    elif topic_id:
        filter_type = 'topic'
        filtered = Topic.objects(id=ObjectId(topic_id)).first()
        posts = [p.id for p in Post.objects(topics=filtered)]
        comments = Comment.objects(post__in=posts)
    elif user_id:
        filter_type = 'user'
        filtered = User.objects(id=ObjectId(user_id)).first()
        comments = Comment.objects(user=filtered)
    elif flag:
        filter_type = 'flag'
        flag_type = flag
        filtered = None
        comments = Comment.objects(flagged=flag_type)
    else:
        filter_type = 'all'
        filtered = None
        comments = Comment.objects.all()

    all_objs = comments
    page = int(request.args.get('page',1))
    q = request.args.get('q','').strip()
    if q:
        posts = Post.objects.filter(headline__icontains=q)
        q1 = Q(post__in=posts)
        q2 = Q(comment__icontains=q)
        all_objs = all_objs.filter(q1|q2)
    pager = Pager(page, PER_PAGE, all_objs, q=q, user_id=user_id)

    return render_template('admin/comments.html',
        pager = pager,
        filtered = filtered,
        filter_type = filter_type,
        flag_type = flag
    )

@admin.route('/admin/delete/comment/<comment_id>')
@roles_required('admin')
def delete_comment(comment_id):
    comment = Comment.objects(id=ObjectId(comment_id)).first()
    comment.delete()
    return redirect(request.referrer)
