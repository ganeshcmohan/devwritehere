import tempfile

ASSETS_DEBUG = True

# 734AstEMAIL

# base domain
HTTP_EXTERNAL_BASE = 'http://localhost:5000'
DEFAULT_EMAIL_DOMAIN = 'writehere.com'

# general settings
PROPAGATE_EXCEPTIONS = True
UPLOADS_DEFAULT_DEST = tempfile.gettempdir()
FLAG_OPINION_TYPES = [(u'abusive', u'Abusive'),
    (u'copyright', u'Copyright'),
    (u'imposter', u'Imposter'),
    (u'offensive', u'Offensive'),
    (u'trademark', u'Trademark'),
    (u'spam', u'Spam')]
FLAG_COMMENT_TYPES = FLAG_OPINION_TYPES

ADDTHIS_SHARES_URL = 'http://api-public.addthis.com/url/shares.json?url=%(url)s'

PAGINATE = 40

SHORT_URL_OPINION = "http://wh.tl/%(code)s"
LONG_URL_OPINION = "http://writehere.com/post/%(code)s/%(slug)s"

# file settings
MAX_CONTENT_LENGTH = 4 * 1024 * 1024

# email settings
FUNDER_MAIL = 'cameron@writehere.com'
ADMIN_MAIL = 'admin@writehere.com'
DEFAULT_MAIL_SENDER = ADMIN_MAIL
AKISMET_KEY = '4a59d9140c4a'

# mongodb settings
MONGODB_DB = 'writehere'
MONGODB_HOST = 'localhost'

# celery and cache
BROKER_TRANSPORT = 'redis'
BROKER_URL = "redis://localhost:6379/15"
BROKER_PORT = 6379
CELERY_RESULT_BACKEND = "redis"
CELERY_REDIS_HOST = "localhost"
CELERY_REDIS_PORT = 6379
CELERY_REDIS_DB = 15
CELERY_RESULT_PORT = 6379
CELERY_IMPORTS = ("app.tasks", )
CELERYD_LOG_FILE="/var/log/celery/celery.log"
CELERYD_LOG_LEVEL="DEBUG"
CELERY_ANNOTATIONS = {
    'app.tasks.addthis_share_update': {'rate_limit': '10/m'}
}

# flask-cache
CACHE_TYPE = 'redis'
CACHE_DEFAULT_TIMEOUT = 60*60
CACHE_REDIS_HOST = 'localhost'
CACHE_REDIS_PORT = 6379

# flask security
SECRET_KEY = '151DF56er54DF1#'

SECURITY_PASSWORD_HASH = 'sha512_crypt'
SECURITY_PASSWORD_SALT = '151DF56eadsfr54DF1@151DFasdf56er54DF1'

OAUTH_LINKEDIN = {
    'consumer_key': 'vbriigiyagly', #'7xuc85j5agc1',
    'consumer_secret': 'cpTTGO7PWMbRuWlc', #'XXXFNU8lIpVBRiHe',
}

OAUTH_TWITTER = {
    'consumer_key': 'JTCa4ytQqT79mf57GJWR6A',
    'consumer_secret': '8i4fgECZlobZsmwXFGDZGC4PpXEC16j6f4TfgUOOVnY'
}

OAUTH_GOOGLE = {
    'consumer_key': '736099019779.apps.googleusercontent.com',
    'consumer_secret': 'ahmV3McsnGezaUbTq6z2wtoA',
    'params': {
        'scope': 'https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/plus.me'
    }
}

OAUTH_FACEBOOK = {
    'consumer_key': '152301828245351',
    'consumer_secret': 'c853b56afb765393ad5258d999c59405',
    'params': {
        'scope': 'email,publish_stream,publish_actions'
    }
}

GOOGLE_SERVICE_ACCOUNT_EMAIL = '313493436749@developer.gserviceaccount.com'
GOOGLE_ANALYTICS_PROFILE_ID = 'ga:68939286'

NY_TIMES_POPULAR = '117fae2ac946624e762a3dcbf8990fe0:14:67390523'
NY_TIMES_TAGS = 'b13bc29fe33603ef6c4f71e182a1ac62:14:67390523'

SQLALCHEMY_DATABASE_URI = 'mysql://flask:734AstSS@localhost/mail'

MAIL_SERVER = 'smtp.zoho.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_USERNAME = 'admin@writehere.com'
MAIL_PASSWORD = 'Wr1teH3re'
DEFAULT_MAIL_SENDER = FUNDER_MAIL

from datetime import datetime
TOPIC_NEW_DATE = datetime(2000,1,1,0,0,0,0)

FACEBOOK_SDK_VERSION = "2.6"

try:
    from local import *
except:
    pass
