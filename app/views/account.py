from flask import Blueprint, request, redirect, url_for
from flask import render_template, flash, jsonify, current_app
from flask import abort, get_flashed_messages
from flask.ext.login import login_required, current_user, login_user
from flask.ext.security.utils import encrypt_password
from bson.objectid import ObjectId

from ..forms import RegisterForm, ProfileForm, UploadForm, CropForm, ForgotPasswordForm, ResetPasswordForm
from ..models import User, Profile, UserRelation, SocialConnection
from ..util import get_user_object, send_mail, br2nl, send_xmail
from ..settings import HTTP_EXTERNAL_BASE, ADMIN_MAIL, DEFAULT_MAIL_SENDER

from .. import forms as f

import uuid

account = Blueprint('account', __name__, template_folder='../templates')

def _send_verify_email(user):
    """docstring for _send_verify_email"""
    link = '%s/account/verify/%s/%s' % (
            HTTP_EXTERNAL_BASE, str(user.id), str(user.verification_uuid))
    send_mail('email/verification.html',
            'Please verify your account at WriteHere..',
            [user.email],
            sender=ADMIN_MAIL,
            html=True,
            context={'verification_link': link},
            )
    flash('A verification email has been sent to your account. When you receive it please click the link to verify.<br>If you do not receive the email in the next minute or so, be sure to check your spam folder; email filters can be a little over-protective sometimes.','success')

@account.route('/welcome')
def welcome():
    return render_template('security/welcome.html')

@account.route('/register', methods=['GET', 'POST'])
@account.route('/register/<provider_id>', methods=['GET', 'POST'])
def register(provider_id=None):
    if current_user.is_authenticated:
        return redirect(request.referrer or '/')

    provider = None
    connection_values = None
    print "register"
    form = RegisterForm()
    print form.email.data,"---","pwddd",form.password.data
    if form.validate_on_submit():
        print "form validate"
        email = form.email.data
        if email.endswith('@yandex.com'):
            flash('sorry, your email address is invalid on this site')
            return redirect(url_for('index'))
        print form.email.data,"---","pwddd",form.password.data
        user = current_app.security.datastore.create_user(email=form.email.data, password=encrypt_password(form.password.data))
        current_app.security.datastore.commit()
        user.username = form.email.data
        user.verification_uuid = str(uuid.uuid4())
        print "saveee"
        user.create()

        profile = Profile.objects(user=user).modify(upsert=True, new=True, display_name=form.display_name.data)

        _send_verify_email(user)
        send_xmail('email/welcome_email.html', 'Welcome to WriteHere',
                [user.email], sender=DEFAULT_MAIL_SENDER, html=True, context={})

        if login_user(user, remember=True):
            return redirect(url_for('account.profile'))

        return render_template('account_profile.html',
            user=user,
            profile=profile,
            form=form
        )
    print "not validate",form.errors
    login_failed = int(request.args.get('login_failed', 0))

    return render_template('security/register.html',
        form=form,
        login_failed=login_failed,
        connection_values=connection_values,
        provider=provider
    )

@account.route('/account/send_verify_email/', methods=['GET'])
@login_required
def send_verify_email():
    user = get_user_object(current_user)
    _send_verify_email(user)
    return redirect(url_for('account.email'))

@account.route('/account/verify/<user_id>/<verification_code>', methods=['GET'])
def verify_email(user_id, verification_code):
    try:
        user = User.objects(id=ObjectId(user_id)).first()
        code = User.objects(verification_uuid=str(verification_code)).first()

        assert user.id == code.id
        assert str(user.verification_uuid) == str(verification_code)

        user.verified = True
        user.save()
    except:
        return abort(404)

    _ = get_flashed_messages()
    flash('Successfully verified your e-mail address!','success')

    return redirect(url_for('account.profile'))

@account.route('/account/email', methods=['GET', 'POST'])
def email():
    user = get_user_object(current_user)
    if user.verified:
        form = f.ChangeEmailForm()
        tmpl = 'account_email.html'
    else:
        form = f.ChangeEmailForm(obj=user)
        tmpl = 'account_email_not.html'

    if form.validate_on_submit():
        email = form.email.data.strip()
        changed = (user.email != email)
        if not changed and user.verified:
            form.email.errors.append('your email has already been verified')
            return render_template(tmpl, form = form)

        if changed:
            others = User.objects(email=email)
            if not others:
                form.email.errors.append('email exists')
                return render_template(tmpl, form = form)
            else:
                user.save()

        if not user.verified or changed:
            _send_verify_email(user)
            #flash('A verification email has been send to you email address, please check it.','success')
        return redirect(url_for('account.email'))

    return render_template(tmpl, form = form)

@account.route('/account/change-password', methods=['GET', 'POST'])
def password():
    user = get_user_object(current_user)
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password = encrypt_password(form.password.data)
        user.save()
        login_user(user, remember=True)
        flash('Successfully updated your password!','success')
        return redirect(url_for('account.password'))

    return render_template('account_password.html',
        form = form,
    )

@account.route('/account/reset/<user_id>/<reset_code>', methods=['GET', 'POST'])
def reset_password(user_id, reset_code):
    form = ResetPasswordForm()
    if form.validate_on_submit():
        try:
            user = User.objects(id=ObjectId(user_id)).first()
            code = User.objects(reset_uuid=str(reset_code)).first()
            assert user.id == code.id
            assert str(user.reset_uuid) == str(reset_code)
        except:
            return abort(404)

        user.password = encrypt_password(form.password.data)
        user.save()
        login_user(user, remember=True)

        flash('Successfully updated your password!')

        return redirect(url_for('account.profile'))

    if request.method == 'GET':
        _ = get_flashed_messages()

    return render_template('change_password.html',
        form = form,
        user_id = user_id,
        reset_code = reset_code
    )


@account.route('/account/forgot-password', methods=['POST'])
def forgot_password():
    form = ForgotPasswordForm()

    if form.validate_on_submit():
        email = form.email.data
        user = User.objects(email=str(email).lower()).first()
        if not user:
            return jsonify({
                'result': False,
                'class': 'alert alert-error',
                'message': "Sorry we couldn't locate that e-mail address."
            })

        user.reset_uuid = str(uuid.uuid4())
        user.save()

        send_mail('email/reset_password.html',
                'WriteHere password reset request..',
                [user.email],
                sender=DEFAULT_MAIL_SENDER,
                html=True,
                context = {
                    'reset_link': '%s/account/reset/%s/%s' % (
                        HTTP_EXTERNAL_BASE,
                        str(user.id),
                        str(user.reset_uuid),
                    )
                })

        return jsonify({
            'result': True,
            'class': 'alert alert-success',
            'message': '<b>Success!</b><br /> Please check your e-mail for further instructions on how to reset your password.'
        })

    return jsonify({
        'result': False,
        'class': 'alert',
        'message': "Invalid e-mail. Please try again."
    })

@account.route('/profile', methods=['GET','POST'])
@account.route('/account/profile', methods=['GET','POST'])
@login_required
def profile():
    """ get current profile, if it exists. else create blank model """
    user = get_user_object(current_user)
    if not user:
        return redirect(url_for('login'))

    try:
        profile = Profile.objects.get(user=user)
    except:
        profile = Profile.objects.create(user=user)

    form = ProfileForm(obj=profile)

    if form.validate_on_submit():
        profile.bio = form.bio.data
        profile.web_presence = form.web_presence.data
        profile.display_name = form.display_name.data
        profile.location = form.location.data
        profile.save()

        flash('Updated Profile!', 'success')

        return render_template('account_profile.html',
            user=user,
            profile=profile,
            form=form,
        )

    if not form.bio.data: form.bio.data = ''
    if not form.web_presence.data: form.web_presence.data = ''

    form.bio.data = br2nl(form.bio.data)
    form.web_presence.data = br2nl(form.web_presence.data)

    return render_template('account_profile.html',
        form=form,
        profile=profile,
        user=user,
    )

@account.route('/follow/<user_id>')
@login_required
def follow(user_id):
    user = get_user_object(current_user)
    to_follow = User.objects(id=ObjectId(user_id)).first()

    if not to_follow or not user:
        return jsonify({'result': False})

    r = UserRelation.objects(user=to_follow, follower=user)
    if r:
        r.delete()
        return jsonify({'result': False})
    else:
        UserRelation.objects.create(user=to_follow, follower=user)
        return jsonify({'result': True})


@account.route('/account/photo')
@login_required
def photo():
    user = current_user
    upload_form = UploadForm()
    crop_form = CropForm()
    return render_template("account_photo.html",
        user=user,
        crop_form=crop_form,
        upload_form=upload_form)

@account.route('/account/connections')
@login_required
def connections():
    user = current_user

    twitter = SocialConnection.objects(user_id=user.id, service_alias='twitter').first()
    google = SocialConnection.objects(user_id=user.id, service_alias='google').first()
    facebook = SocialConnection.objects(user_id=user.id, service_alias='facebook').first()
    linkedin = SocialConnection.objects(user_id=user.id, service_alias='linkedin').first()

    return render_template("account_connections.html",
        user = user,
        twitter = twitter,
        google = google,
        facebook = facebook,
        linkedin = linkedin
    )

@account.route('/disconnect/<service_alias>')
@login_required
def disconnect(service_alias):
    connections = SocialConnection.objects(
        user_id=current_user.id,
        service_alias__ne=service_alias).count()

    if connections < 1 and current_user.oauth_only:
        flash("Sorry, you can't delete your last connection.", "error")
        return redirect(request.referrer)

    connection = SocialConnection.objects(
        user_id=current_user.id,
        service_alias=service_alias).first()

    if connection: connection.delete()

    flash("Successfully removed connection to %s." % service_alias, "success")
    return redirect(request.referrer)


@account.route('/delete-user/<user_id>')
@login_required
def delete_user(user_id):
    user = User.objects(id=ObjectId(user_id)).first()
    if user:
        if current_user == user:
            UserRelation.objects(user=user).delete()
            UserRelation.objects(follower=user).delete()
            user.delete()
    return redirect(url_for('index'))
