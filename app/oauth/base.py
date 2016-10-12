from datetime import datetime, timedelta

from flask import url_for, request, flash, redirect, session, \
                  get_flashed_messages, current_app
from flask_login import current_user
from flask.ext.security.utils import login_user

from ..models import SocialConnection, Profile

class AbstractRAuth(object):
    client = None

    @property
    def name(self):
        raise NotImplementedError

    @property
    def options(self):
        raise NotImplementedError

    @classmethod
    def get_credentials(cls, response, oauth_token):
        raise NotImplementedError

    @classmethod
    def authorize(cls, response, oauth_token):
        _ = get_flashed_messages()
        next_url = session.pop('oauth_callback_url_' + str(cls.name), url_for('index'))
        if response is None or 'denied' in request.args:
            flash(u'You denied the request to sign in.', "error")
            return redirect(next_url)

        #try:
        credentials = cls.get_credentials(response, oauth_token)
        #except Exception:
        #    return redirect(next_url)

        if credentials.get('expires'):
            expires_in = timedelta(seconds=int(credentials['expires']))
            credentials['expires'] = datetime.now() + expires_in

        user = current_user
        key = SocialConnection.objects(service_alias=cls.name, service_id=credentials['service_id']).first()

        if key:
            if user.is_authenticated:
                if key.user_id != user.id:
                    flash('Sorry, that %s account is already associated with another WriteHere account.' % str(cls.name), 'error')
                    return redirect(next_url)
            else:
                user = key.user
            key.access_token=credentials['access_token']
            key.refresh_token=credentials.get('refresh_token')
            key.secret=credentials.get('secret')
            key.expires=credentials.get('expires')
            key.contact_info = credentials.get('contact_info')
            key.save()
        else:
            if not user.is_authenticated:
                user = current_app.security.datastore.create_user(
                    email=cls.name + '_' + credentials['service_id'],
                    username=credentials['username'],
                    password='')
                current_app.security.datastore.commit()

                Profile.objects(user=user).modify(
                    upsert=True,
                    new=True,
                    display_name=user.username,
                    bio=credentials.get('bio', ''),
                )

                user.oauth_only = True
                user.generate_password()
                user.create()

            key = SocialConnection(
                service_alias=cls.name,
                user_id=user.id,
                service_id=credentials['service_id'],
                access_token=credentials['access_token'],
                refresh_token=credentials.get('refresh_token'),
                secret=credentials.get('secret'),
                expires=credentials.get('expires'),
                verifier=credentials.get('verifier', None),
                contact_info=credentials.get('contact_info'),
            )
            key.save()

        login_user(user, remember=True)
        flash('Successfully connected to %s.' % cls.name, "success")
        return redirect(next_url)

    @classmethod
    def setup(cls, app):
        options = app.config.get('OAUTH_%s' % cls.name.upper())
        if not options:
            return False

        params = dict()
        if 'params' in options:
            params = options.pop('params')

        app.logger.info('Init OAuth %s' % cls.name)
        cls.options.update(name=cls.name, **options)
        from flask_rauth import RauthOAuth2, RauthOAuth1
        client_cls = RauthOAuth2
        if cls.options.get('request_token_url'):
            client_cls = RauthOAuth1

        if cls.name == 'linkedin':
            params['params'] = {'scope': 'rw_nus'}

        cls.client = client_cls(**cls.options)

        login_name = '/login/%s' % cls.name
        authorize_name = '/connect/%s' % cls.name

        @app.route('/login/%s' % cls.name, endpoint=login_name)
        def login():
            ref = url_for('account.profile') if '/register' in str(request.referrer) else request.referrer
            session['oauth_callback_url_' + str(cls.name)] = request.args.get('next') or ref or url_for('index')
            return cls.client.authorize(
                callback=(
                    url_for(authorize_name, _external=True)
                ), **params)

        cls.client.tokengetter_f = cls.get_token

        app.add_url_rule('/connect/%s' % cls.name,
            authorize_name,
            cls.client.authorized_handler(cls.authorize))

    @classmethod
    def get_token(cls):
        if current_user.is_authenticated:
            for key in current_user.social_connections:
                if key.service_alias == cls.name:
                    return key.access_token
