from .base import AbstractRAuth

class GoogleOAuth(AbstractRAuth):

    name = 'google'
    options = dict(
        base_url='https://www.googleapis.com/oauth2/v1/',
        access_token_url='https://accounts.google.com/o/oauth2/token',
        authorize_url='https://accounts.google.com/o/oauth2/auth',
    )

    @classmethod
    def get_credentials(cls, response, oauth_token):
        me = cls.client.get('userinfo', access_token=oauth_token)

        handle = me.content.get('email')
        if not handle:
            handle = me.content.get('link')

        return dict(
            username = me.content['name'],
            access_token = oauth_token,
            expires = response.content['expires_in'],
            service_id = me.content['id'],
            contact_info = handle,
        )