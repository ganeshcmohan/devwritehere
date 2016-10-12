#!/sites/venv/bin/python

from sh import chgrp, chown, chmod, maildirmake, sudo
with sudo:
    maildirmake('/var/vmail/writehere.com/test4')
    chgrp('mail', '-R', '/var/vmail/writehere.com/test4')
    chown('vmail', '-R', '/var/vmail/writehere.com/test4')
    chmod('u+rwx',  '-R', '/var/vmail/writehere.com/test4')