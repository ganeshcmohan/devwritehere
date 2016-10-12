from .twitter import TwitterOAuth
from .google import GoogleOAuth
from .linkedin import LinkedInOAuth
from .facebook import FacebookOAuth


PROVIDERS = [TwitterOAuth, GoogleOAuth, FacebookOAuth, LinkedInOAuth]