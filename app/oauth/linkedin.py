from .base import AbstractRAuth

class LinkedInOAuth(AbstractRAuth):

    name = 'linkedin'
    options = dict(
        base_url='http://api.linkedin.com/v1/',
        authorize_url='https://www.linkedin.com/uas/oauth/authenticate',
        access_token_url='https://api.linkedin.com/uas/oauth/accessToken',
        request_token_url='https://api.linkedin.com/uas/oauth/requestToken'
    )

    @classmethod
    def get_credentials(cls, response, oauth_token):
        #access_token, access_token_secret = oauth_token
        me = cls.client.get('people/~:(id,first-name,last-name,formatted-name,public-profile-url,picture-url)', oauth_token=oauth_token,
            params = {
                'format':'json',
                'scope': 'rw_nus'
            }
        )

        from urlparse import urlparse
        from werkzeug.urls import url_decode
        parts = urlparse(response.response.url)
        query = parts[4]
        parts = url_decode(query)

        handle = me.content.get('publicProfileUrl')
        if not handle:
            handle = me.content.get('formattedName')

        return dict(
            username=me.content['formattedName'],
            service_id=me.content['id'],
            access_token=response.content['oauth_token'],
            secret=response.content['oauth_token_secret'],
            expires=response.content['oauth_authorization_expires_in'],
            verifier=parts['oauth_verifier'],
            contact_info=handle
        )
