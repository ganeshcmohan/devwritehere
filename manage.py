#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from flask.ext.assets import ManageAssets
from flask.ext.script import Manager
from flask.ext.security.script import CreateUserCommand
# from flask.ext.celery import install_commands as install_celery_commands
from app import create_app
from app import script as s

manager = Manager(create_app())
manager.add_command("assets", ManageAssets())
manager.add_command('create_user', CreateUserCommand())
manager.add_command('import_topics', s.ImportTopicsCommand())
manager.add_command('clear_topics', s.ClearTopicsCommand())
manager.add_command('send_xmail', s.SendXmailCommand())
manager.add_command('addthis_update', s.AddThisUpdateCommand())
manager.add_command('test_fb', s.TestFBCommand())
manager.add_command('exp', s.ExportPostsCommand())
manager.add_command('mongoengine_upgrade', s.UpgradeMongoengineCommand())
# install_celery_commands(manager)

if __name__ == "__main__":
    manager.run()
