from markdown import markdown
from flask import make_response, render_template
from flask.ext.mail import Message

from HTMLParser import HTMLParser
from werkzeug import url_decode
from functools import update_wrapper

import re
import unidecode
import hashlib, base64, hmac, pytz, datetime

from settings import SECURITY_PASSWORD_SALT, DEFAULT_MAIL_SENDER
from extensions import mail

salt = SECURITY_PASSWORD_SALT

_urlfinderregex = re.compile(r'http([^\.\s]+\.[^\.\s]*)+[^\.\s]{2,}', re.IGNORECASE)


def urlify(text,limit=None):
    """
    show https://www.abc.com to:
    <a href="https://www.abc.com">abc.com</a>
    """
    def replacewithlink(matchobj):
        url = matchobj.group(0)
        text = unicode(url)
        text = url.rstrip('/')
        k = 'https://'
        if text.startswith(k):
            text = text[len(k):]
        k = 'http://'
        if text.startswith(k):
            text = text[len(k):]
        k = 'www.'
        if text.startswith(k):
            text = text[len(k):]
        if limit:
            if len(text) > limit:
               text = text[:limit] + '...'
        return '<a href="' + url + '" target="_blank" rel="nofollow">' + text + '</a>'
    if text is not None and text != '':
        return _urlfinderregex.sub(replacewithlink, text)
    else:
        return ''


class MethodRewriteMiddleware(object):

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if 'METHOD_OVERRIDE' in environ.get('QUERY_STRING', ''):
            args = url_decode(environ['QUERY_STRING'])
            method = args.get('__METHOD_OVERRIDE__')
            if method:
                method = method.encode('ascii', 'replace')
                environ['REQUEST_METHOD'] = method
        return self.app(environ, start_response)

class HTTPMethodOverrideMiddleware(object):
    """The HTTPMethodOverrideMiddleware middleware implements the hidden HTTP
    method technique. Not all web browsers support every HTTP method, such as
    DELETE and PUT. Using a querystring parameter is the easiest implementation
    given Werkzeug and how middleware is implemented. The following is an
    example of how to create a form with a PUT method:

        <form action="/stuff/id?__METHOD__=PUT" method="POST">
            ...
        </form>
    """
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if '__METHOD__' in environ.get('QUERY_STRING', ''):
            args = url_decode(environ['QUERY_STRING'])
            method = args.get('__METHOD__').upper()
            if method in ['GET', 'POST', 'PUT', 'DELETE']:
                method = method.encode('ascii', 'replace')
                environ['REQUEST_METHOD'] = method
        return self.app(environ, start_response)

def nocache(f):
    def new_func(*args, **kwargs):
        resp = make_response(f(*args, **kwargs))
        resp.cache_control.no_cache = True
        return resp
    return update_wrapper(new_func, f)

def get_user_object(user_proxy):
    if user_proxy:
        return user_proxy._get_current_object()
    else:
        return None

class MLStripper(HTMLParser):
    def __init__(self, preserve_entities=True):
        self.reset()
        self.fed = []
        if preserve_entities:
            self.preserve = True
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def html_to_text(html):
    s = MLStripper(True)
    s.feed(html)
    return s.get_data()

def formatted_date(d):
    # by guoqiao
    return d.strftime('%Y-%m-%d %H:%M:%S')
    #month = d.strftime('%b')
    #return '{month} {d.day}, {d.year}'.format(
        #d=d,
        #month=month,
    #)

def split_first_space(val):
    val = val or ''
    return val.replace(' ', '<br />', 1)

def split_first_name(val):
    val = val or ''
    parts = val.split(' ')
    if len(parts):
        return parts[0]
    else:
        return 'Unknown'

def space_to_break(val):
    val = val or ''
    return val.replace(' ', '<br />').replace('\r\n', '<br />')

def split_sentences(paragraph):
    sentence_endings = re.compile(r"""
        # Split sentences on whitespace between them.
        (?:               # Group for two positive lookbehinds.
          (?<=[.!?])      # Either an end of sentence punct,
        | (?<=[.!?]['"])  # or end of sentence punct and quote.
        )                 # End group of two positive lookbehinds.
        (?<!  Mr\.   )    # Don't end sentence on "Mr."
        (?<!  Mrs\.  )    # Don't end sentence on "Mrs."
        (?<!  Jr\.   )    # Don't end sentence on "Jr."
        (?<!  Dr\.   )    # Don't end sentence on "Dr."
        (?<!  Prof\. )    # Don't end sentence on "Prof."
        (?<!  Sr\.   )    # Don't end sentence on "Sr."
        \s+               # Split on whitespace between sentences.
        """,
        re.IGNORECASE | re.VERBOSE)
    sentence_list = sentence_endings.split(paragraph)
    return sentence_list

def strip_tags(value):
    """Returns the given HTML with all tags stripped."""
    return re.sub(r'<[^>]*?>', '', value)

def extract_chars(str, chars=150):
    if len(str) > chars:
        return str[:chars]
    else:
        return str

def extract_words(str, words=20):
    """ Extracts the first 25 words from a given content string
    """
    return ' '.join(str.split(' ')[:words])\
        .replace('\n', '')\
        .replace('<br />', '')

def clean_breaks(string):
    string = string.replace('<span>', '').replace('</span>', '')
    string = string.replace("&nbsp;", ' ')
    string = string.replace('\r\n', '<br>')
    string = string.replace('\r', '').replace('\n', '')
    return string

def unclean_breaks(string):
    return string.replace('<br>', '\r\n')

def nl2br(string):
    return string.replace('\n','<br />\n')
    #string = string.replace('\r', '')

def nl2brnl(string):
   return string.replace('\n', '<br />')

def br2nl(string):
    return string.replace('<br />\n', '\n').replace('<br>', '\n')

def hashed(string):
    h = hmac.new(salt, string, hashlib.sha512)
    return base64.b64encode(h.digest())

def naive_to_utc(dt, tz):
    tz = pytz.timezone(tz)
    return tz.normalize(tz.localize(dt)).astimezone(pytz.utc)

def to_utc(dt):
    return dt.replace(tzinfo=pytz.utc)

def from_utc(dt, tz):
    """ inverse of to_utc """
    tz = pytz.timezone(tz)
    utc = pytz.timezone('UTC')
    return utc.normalize(dt).astimezone(tz)

def next_weekday(tz='US/Central', hour=0):
    today = datetime.datetime.utcnow()
    today = today.replace(tzinfo=pytz.utc)
    central = from_utc(today, tz)
    dow = central.timetuple().tm_wday
    if dow == 4:
        delta = 3
    elif dow == 5:
        delta = 2
    else:
        delta = 1
    next_day = central + datetime.timedelta(days=delta)
    next_day = datetime.datetime.combine(next_day.date(), datetime.time(hour=hour))
    next_day = next_day.replace(tzinfo=pytz.timezone(tz))
    return next_day.astimezone(pytz.utc)

def get_first_day_of_month(dt, d_years=0, d_months=0):
    # d_years, d_months are "deltas" to apply to dt
    y, m = dt.year + d_years, dt.month + d_months
    a, m = divmod(m-1, 12)
    return datetime.date(y+a, m+1, 1)

def get_last_day_of_month(dt):
    return get_first_day_of_month(dt, 0, 1) + datetime.timedelta(-1)


def week_begin_end_dates(dt):
    year = int(int(dt.strftime('%Y')))
    week = dt.isoweekday()
    d = datetime.date(year, 1, 1)
    delta_days = d.isoweekday() - 1
    delta_weeks = week
    if year == d.isocalendar()[0]:
        delta_weeks -= 1
        # delta for the beginning of the week
    delta = datetime.timedelta(days=-delta_days, weeks=delta_weeks)
    weekbeg = d + delta
    # delta2 for the end of the week
    delta2 = datetime.timedelta(days=6-delta_days, weeks=delta_weeks)
    weekend = d + delta2
    return weekbeg, weekend


class dotdict(dict):
    def __init__(self,arg):
        for k in arg.keys():
            if type(arg[k]) is dict:
                self[k]=dotdict(arg[k])
            else:
                self[k]=arg[k]
    def __getattr__(self, attr):
        return self.get(attr, None)

    def __dir__(self):
        return self.keys()

    __setattr__= dict.__setitem__
    __delattr__= dict.__delitem__

def send_xmail(template, subject, recipients, sender=DEFAULT_MAIL_SENDER, html=True, context={}):
    body = render_template(template,
        html = html,
        **context
    )
    from models import Xmail
    obj = Xmail()
    obj.subject = subject
    obj.body = body
    obj.sender = sender
    obj.recipients = recipients
    obj.save()

def send_mail(template, subject, recipients, sender=DEFAULT_MAIL_SENDER, html=True, context={}):

    text_body = render_template(template,
        html = False,
        **context
    )

    html_body = render_template(template,
        html = html,
        **context
    )


    msg = Message(
        str(subject),
        sender=sender,
        recipients=recipients
    )

    msg.body = text_body
    msg.html = html_body
    mail.send(msg)

    return True

def md2page(md):
    start = ''
    x = []
    heading = ''
    inner = ''
    is_start = True
    lines = md.splitlines(True)
    for line in lines:
        if line.startswith('##'):
            is_start = False
            if heading and inner:
                heading = heading.strip('##').strip()
                inner = markdown(inner)
                a = {'heading': heading, 'inner': inner}
                x.append(a)
            heading = line
            inner = ''
            continue
        if is_start:
            start += line
            continue
        else:
            inner += line
    if heading and inner:
        heading = heading.strip('##').strip()
        inner = markdown(inner)
        a = {'heading': heading, 'inner': inner}
        x.append(a)
    mdp = {}
    mdp['start'] = markdown(start)
    mdp['x'] = x
    return mdp

