# Writehere.com

## Summary

Writehere is a blog site based on:

* Flask
* MongoDB
* Redis
* elsticsearch
* bootstrap

To make development and deployment easy, we use docker and docker-compose to run this site.

However, docker only works in Linux. So for non-linux developers, we also need vagrant.

## Clone the code and checkout the docker branch:

    git clone git@bitbucket.org:WriteHere/writehere.git ~
    cd ~/writehere
    git checkout docker

Don't worry, both mongodb.tar.gz and mongodb dir are ignored by git.
Keep the mongodb dir there, it will be used by vagrant.

## Install vagrant:

    https://www.vagrantup.com/

DO NOT use boot2docker, there're a lot of issues.

## Start vagrant vm:

    cd ~/writehere
    vagrant up

vagrant will download a box with docker installed for you. Then:

    vagrant ssh

## Download mongodb sample data for dev in vagrant:

    sudo -i
    cd /var/lib
    wget http://static.writehere.com/mongodb.tar.gz
    tar -xzf mongodb.tar.gz
    chown -R root:root mongodb
    chmod -R 777 mongodb
    exit

Note: some how we must download this inside the vagrant vm.
If we do it on localhost and mount to vagrant, there will be permmissin issues from virtualbox.

Now, you are in vagrant as user vagrant.
vagrant has mounted the code dir to /vagrant. Go to code root:

    cd /vagrant

##  Run site via docker-compose:

    docker-compose up

For the first time, it will pull and build other docker images, like redis.
Once finished, in host broswer:

    http://localhost:5000

You should be able to see the site now.
