from fabric.api import env, local, cd, run
from path import path
from os.path import dirname,abspath
HERE = path(dirname(abspath(__file__)))
PROJ_NAME = HERE.name
PROJ_ROOT = path('/srv/src/')/PROJ_NAME

env.use_ssh_config = True
env.hosts = ['writehere.com']
env.base_dir = PROJ_ROOT

def scss():
    with cd(env.base_dir):
        run('scss app/static/scss/main.scss:app/static/css/main.css')

def pull():
    local('git push')
    with cd(env.base_dir):
        run('git pull')
    scss()

def tail():
    run('tail -f /var/log/uwsgi/%s.log' % PROJ_NAME)

def touch():
    run("touch /etc/uwsgi/vassals/%s.ini" % PROJ_NAME)
    tail()

def all():
    pull()
    scss()
    touch()
