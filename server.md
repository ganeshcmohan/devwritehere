# hostname: writehere

# firewall based on here: http://library.linode.com/securing-your-server
# *** Changed ssh to port 8888

sudo iptables-restore < /etc/iptables.firewall.rules

# startup script for firewall
/etc/network/if-pre-up.d/firewall

# install python requirements
$ sudo apt-get install build-essential python-dev python-pip checkinstall nginx git


Setup Virtualenv
----------------
$ sudo pip install virtualenv
$ sudo virtualenv /sites/venv

Setup directories
-----------------
$ sudo mkdir /sites


# Configure nginx
# vim /etc/nginx/nginx.conf
# add this in http directive:
    include /sites/*/conf/nginx.conf;

# config file for site(s)
# vim /sites/writehere.com/conf/nginx.conf

    server {
        listen          80;
        server_name     writehere.com;
        access_log      off;
        error_log       /var/logs/nginx/error.log;

        location / {
            include     uwsgi_params;
            uwsgi_pass  127.0.0.1:9001;
        }

        location /static {
            alias       /sites/writehere.com/static/;
            index       index.html index.htm;
            add_header  Cache-Control "public, max-age=30";
        }
    }


# setup uwsgi
$ sudo pip install uwsgi

# /etc/init/uwsgi.conf

    description "uWSGI server running emperor mode"

    start on runlevel [2345]
    stop on runlevel [!2345]

    respawn

    exec /usr/local/bin/uwsgi --emperor "/sites/*/uwsgi.ini" --catch-exceptions --cpu-affinity 1
    
# /sites/writehere.com/uwsgi.ini

    [uwsgi]
    module           = wsgi:application
    socket           = 127.0.0.1:9001
    uid              = www-data
    gid              = www-data
    processes        = 4
    listen           = 2048
    no-orphans       = true
    chdir            = /sites/writehere.com
    virtualenv       = /sites/venv
    disable-logging  = true
    catch-exceptions = true
    vacuum           = true
    ignore-sigpipe   = true
    close-on-exec    = true

    


# setup mongodb and security

pip install https://github.com/sbook/flask-mongoengine/tarball/master
pip install http://github.com/pythonforfacebook/facebook-sdk/tarball/master
pip install https://github.com/mattupstate/flask-social/tarball/develop

# setup jpeg image support for pillow
sudo apt-get install libjpeg62-dev libfreetype6 libfreetype6-dev zlib1g-dev

# installing redis/caching
sudo apt-get install checkinstall
sudo curl http://redis.googlecode.com/files/redis-2.6.7.tar.gz | sudo tar xz
cd redis-2.6.7 && sudo checkinstall --default --pkgname=redis --pkgversion=2.6.7

# configure redis
sudo vim /etc/init/redis.conf
sudo vim /etc/redis.conf
sudo useradd --home /var/db/redis --shell /bin/false redis
sudo mkdir --parents --mode=0750 /var/db/redis && sudo chown redis: /var/db/redis
sudo start redis

# removing redis /usr/local/src/redis-2.6.2/redis_2.6.2-1_amd64.deb
# dpkg -r redis

# setup search
pip install rawes
wget https://github.com/downloads/elasticsearch/elasticsearch/elasticsearch-0.19.11.zip
unzip elasticsearch-0.19.11.zip
mv elasticsearch-0.19.11 elasticsearch && rm elasticsearch-*.zip
mv elasticsearch-0.19.11/ elasticsearch
sudo mv elasticsearch* /usr/local/elasticsearch

vim /etc/init/elasticsearch.conf
vim /usr/local/elasticsearch/config/elasticsearch.yml

Setup mysql for e-mail
pip install flask-sqlalchemy

sudo apt-get build-dep python-mysqldb

pip install -U distribute
pip install mysql-python


# install akismet
pip install git+git://github.com/joshpurvis/python-akismet.git

# celery
pip install celery-with-redis
pip install flask-celery

pip install https://github.com/mrgaaron/LinkedIn-Client-Library/archive/master.zip

pip install http://pypi.python.org/packages/source/l/lxml/lxml-2.2.8.tar.gz

curl https://gdata-python-client.googlecode.com/files/gdata-2.0.17.tar.gz | tar xz
cd gdata<Tab>
python setup.py install


Getting this?

TypeError: session() takes no arguments (1 given)

Must use old ass version of requests because of flask_rauth/rauth:
- fix requests (not related to oauth)
pip install --upgrade Flask-Rauth==0.2.2
pip install --upgrade rauth==0.4.17
pip install --upgrade requests=0.14.2