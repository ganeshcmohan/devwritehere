from flask import Blueprint, render_template, request, url_for, jsonify, current_app
from flask.ext.login import current_user

from bson.objectid import ObjectId
from ..models import Post
from ..util import get_user_object, html_to_text
from ..settings import PAGINATE

search = Blueprint('search', __name__, template_folder='../templates')

def search_simple_opinions(query, start=0, size=10, sort="_score"):

    data = {
        "size":size,
        "from":start,
        "sort":[
            "_score"
        ],
        "query":{
            "filtered":{
                "query":{
                    "bool":{
                        "should":[
                            {
                                "text":{
                                    "headline":{
                                        "boost":5,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "headline.partial":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "headline.partial_middle":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "headline.partial_back":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },

                            # content
                            {
                                "text":{
                                    "content":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "content.partial":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "content.partial_middle":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "content.partial_back":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },


                            # topics
                            {
                                "text":{
                                    "topics":{
                                        "boost":5,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "topics.partial":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "topics.partial_middle":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "topics.partial_back":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },

                            # author name
                            {
                                "text":{
                                    "author_name":{
                                        "boost":5,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "author_name.partial":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "author_name.partial_middle":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "author_name.partial_back":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },

                            ]
                    }
                },

                }
        }
    }

    with current_app.app_context():
        rs = current_app.es.get('opinions/opinion/_search', data=data)

        posts = []
        post_ids = []
        if rs:
            hits = rs.get('hits', {}).get('hits', [])
            for hit in hits:
                try:
                    post  = Post.objects(id=ObjectId(hit['_id'])).first()
                except:
                    post = None
                if post and str(post.id) not in post_ids:
                    topics = [
                        {'name': topic.topic, 'url': url_for('show_topic', slug=topic.slug)}
                        for topic in post.topics
                    ]
                    post_ids.append(str(post.id))
                    post_json = {
                        'opinion_url': post.url,
                        'photo_orientation': post.photo_orientation,
                        'photo_url': post.photo_url,
                        'user_id': str(post.user.id),
                        #'post_id': str(post.id),
                        'opinion_id': str(post.id),
                        'headline': post.headline,
                        'opinion_my_page':post.user.my_page_anchor,
                        'views': post.views,
                        'shares': post.shares,
                        'comments': post.comments,
                        'timestamp': post.timestamp,
                        'opinion_update_url' : url_for('write.update_opinion', opinion_id=post.id),
                        'opinion_delete_url' : url_for('write.delete_opinion', opinion_id=post.id),
                        'opinion_my_page_url': url_for('write.my_page', date_slug=post.user.date_slug, display_name_slug=post.user.display_name_slug),
                        'extract': html_to_text(post.extract),
                        'opinion_write_url': url_for('write.write_opinion', post_id=post.id),
                        'topic_list': topics,
                        'hover_edit' : '',
                        'is_draft' : '',
                        'is_spam' : '',
                        'topic_count': len(topics),
                    }
                    posts.append(post_json)

        return posts


def autocomplete_opinions(query, start=0, size=10):

    data = {
        "size":size,
        "from":start,
        "sort":[
            "_score"
        ],
        "query":{
            "filtered":{
                "query":{
                    "bool":{
                        "should":[
                            {
                                "text":{
                                    "headline":{
                                        "boost":5,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "headline.partial":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "headline.partial_middle":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "headline.partial_back":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },

                            # content
                            {
                                "text":{
                                    "content":{
                                        "boost":5,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "content.partial":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "content.partial_middle":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "content.partial_back":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },


                            # topics
                            {
                                "text":{
                                    "topics":{
                                        "boost":5,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "topics.partial":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "topics.partial_middle":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "topics.partial_back":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },


                            # author name
                            {
                                "text":{
                                    "author_name":{
                                        "boost":5,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "author_name.partial":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "author_name.partial_middle":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },
                            {
                                "text":{
                                    "author_name.partial_back":{
                                        "boost":1,
                                        "query":query,
                                        "type":"phrase"
                                    }
                                }
                            },



                        ]
                    }
                },

            }
        }
    }

    with current_app.app_context():
        rs = current_app.es.get('opinions/opinion/_search', data=data)
        posts = []
        if rs:
            hits = rs.get('hits', {}).get('hits', [])
            for hit in hits:
                posts.append(hit)


        return posts

@search.route('/search/autocomplete', methods=['GET'])
def search_autocomplete():
    query = request.args.get('query', '')
    posts = autocomplete_opinions(query, 0, 10)

    post_list = []
    for post in posts:
        #post_list.append({
            #'id' : post['_source']['url'],
            #'name' : post['_source']['headline']
        #})
        headline = post['_source']['headline']
        max_len = 30
        if len(headline) > max_len:
            headline = headline[:max_len] + '...'
        post_list.append(headline)

    return jsonify({
        'result': True if post_list else False,
        'items': post_list
    })

@search.route('/search', methods=['GET'])
def search_index():
    query = request.args.get('query')
    user = get_user_object(current_user)

    return render_template('search.html',
        user = user,
        query = query,
    )

@search.route('/search/json', methods=['GET'])
def search_json():
    query = request.args.get('query')
    start = int(request.args.get('start', 0))
    sort = request.args.get('sort')
    writers = request.args.get('writers')

    if sort == 'latest':
        order_by = '-date_updated_timestamp'
    elif sort == 'opinions':
        order_by = '-posts'
    elif sort == 'comments':
        order_by = '-comment_increment'
    elif sort == 'views':
        order_by = '-views'
    elif sort == 'shares':
        order_by = '-shares'
    else:
        order_by = '-id'

    limit = PAGINATE
    #TODO: for ordering and follow
    posts = search_simple_opinions(query, start, start+limit)

    if posts:
        return jsonify({
            'result': True,
            'opinions': posts,
            'start': start + limit
        })
    else:
        return jsonify({
            'result': False,
            'opinions': []
        })


@search.route('/search/search/<keywords>')
def test_search2(keywords):
    rs = search_simple_opinions(keywords)
    return jsonify(rs)
