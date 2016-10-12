from .base import AbstractRAuth

class TwitterOAuth(AbstractRAuth):

    name = 'twitter'
    options = dict(
        base_url='https://api.twitter.com/1/',
        authorize_url='https://api.twitter.com/oauth/authorize',
        access_token_url='https://api.twitter.com/oauth/access_token',
        request_token_url='https://api.twitter.com/oauth/request_token',
    )

    @classmethod
    def get_credentials(cls, response, oauth_token):
        me = cls.client.get('users/show.json?screen_name=%(sn)s' % {'sn': response.content['screen_name']} )

        return dict(
            username=response.content['screen_name'],
            contact_info=response.content['screen_name'],
            service_id=response.content['user_id'],
            access_token=response.content['oauth_token'],
            secret=response.content['oauth_token_secret'],
            bio=me.content.get('description', '')
        )
