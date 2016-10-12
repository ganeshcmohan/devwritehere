#!/sites/venv/bin/python

from sh import sudo, rm
with sudo:
    rm('/var/vmail/writehere.com/test4', '-R')
