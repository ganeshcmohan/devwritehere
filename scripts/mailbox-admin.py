#!/sites/venv/bin/python

from sh import chgrp, chown, chmod, maildirmake, rm, sudo, ErrorReturnCode
import argparse
from sys import stderr

MAILBOX_BASE_PATH = '/var/vmail'
PATH_FORMAT = '%s/%s/%s'
DOMAIN = 'writehere.com'

def create_mailbox(mailbox, domain=DOMAIN):
    mailbox_path = PATH_FORMAT % (MAILBOX_BASE_PATH, domain, mailbox)
    with sudo:
        try:
            maildirmake(mailbox_path)
            chgrp('mail', '-R', mailbox_path)
            chown('vmail', '-R', mailbox_path)
            chmod('u+rwx',  '-R', mailbox_path)
        except ErrorReturnCode:
            print_error("Error: Fail to create mailbox. Check permissions?")

def delete_mailbox(mailbox, domain=DOMAIN):
    mailbox_path = PATH_FORMAT % (MAILBOX_BASE_PATH, domain, mailbox)
    with sudo:
        try:
            rm(mailbox_path, '-R')
        except ErrorReturnCode:
            print_error("Error: Failed to remove mailbox. Check Permissions?")

def print_error(error, show_help=True):
    if show_help: parser.print_help()
    stderr.write(error + '\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mailbox',
        type=str,
        action='store',
        default=False,
        help="Name of mailbox."
    )
    parser.add_argument('--create', '-c',
        dest="create",
        action='store_true',
        default=False,
        help="Create given mailbox name."
    )
    parser.add_argument('--delete', '-d',
        dest="delete",
        action='store_true',
        default=False,
        help="Delete given mailbox name."
    )

    results = parser.parse_args()

    if results.mailbox:
        if results.create:
            create_mailbox(results.mailbox)
        elif results.delete:
            delete_mailbox(results.mailbox)
        else:
            print_error('Error: Please specify an operation. Example: $ mailbox-admin.py --create mymailbox')
    else:
        print_error('Error: No mailbox specified.')
