from flask import Blueprint, request, render_template, jsonify
from app.tasks import fb_post_opinion, social_post_task
from ..models import Page, SocialConnection

from ..tasks import addthis_share_update
import datetime
from bson.objectid import ObjectId
from ..util import md2page

general = Blueprint('general', __name__, template_folder='../templates')

@general.route('/test/addthis')
def addthis_share_test():
    return addthis_share_update()

def page(slug,tmpl='page'):
    page = Page.objects.get(slug=slug)
    mdp = md2page(page.content)
    slugs = ['flag-it', 'service-commitment', 'write-to-us']
    for slug in slugs:
        tips = Page.objects(slug__in=slugs)
    pjax = request.headers.get('X-PJAX', False)
    if pjax:
        tmpl = '%s_inc.html' % tmpl
    else:
        tmpl = '%s.html' % tmpl
    return render_template(tmpl, page=page, pjax=pjax, mdp=mdp, tips=tips)

@general.route('/guidelines')
def guidelines():
    return page('guidelines')

@general.route('/faq')
def faq():
    return page('faq')

@general.route('/about-writehere')
def about_writehere():
    return page('about-writehere')

@general.route('/about-us')
def about_us():
    return page('about-us')

@general.route('/writing-tips')
def writing_tips():
    return page('writing-tips')

@general.route('/fb-test')
def facebook_test():
    fb_post_opinion.apply_async(args=['507371a4fe7e313d5a4f1e1e', '50c91802fe7e312f087094fe'])
    return 'non'
    #return 'Done!'

@general.route('/general/social-post-cron')
def social_post_cron():
    social_post_task.apply_async()
    return "Queued task"

@general.route('/gdata')
def gdata_test():
    import app.analytics.analytics as ga
    service = ga.get_service()
    return jsonify(ga.get_visitors_by_country(service))


@general.route('/general/reset-tokens')
def reset_tokens():
    connections = SocialConnection.objects(user_id=ObjectId("5104462fa8ee691988fc4e6b"))  #ObjectId('507f5771fe7e31092dbf65fc'))
    for con in connections:
        if con.service_alias not in ['twitter']:
            con.expires = datetime.datetime.utcnow()
            con.save()
    return 'Completed'
