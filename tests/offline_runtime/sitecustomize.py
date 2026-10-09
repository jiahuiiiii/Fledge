"""Block network egress in disposable browser processes, including seed scripts.

Loaded explicitly by disposable pytest/browser commands through PYTHONPATH.
The normal app and real-source evaluations never load this test helper.
"""
import os
import socket

if os.environ.get('THESIS_TEST_OFFLINE') == 'true':
    if not os.environ.get('THESIS_DATA_DIR','').startswith(('/private/tmp/thesis-browser-', '/private/tmp/thesis-test-')):
        # Python ignores ordinary sitecustomize exceptions and continues startup.
        # An incorrectly configured test must stop, never silently lose its guard.
        raise SystemExit('Offline test guard requires a disposable test directory')
    local = {None, 'localhost', '127.0.0.1', '::1'}
    original_dns = socket.getaddrinfo
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def resolve(host, *args, **kwargs):
        if host not in local:
            raise OSError('External networking is disabled in this browser fixture')
        return original_dns(host, *args, **kwargs)

    def connect(self, address):
        if self.family != socket.AF_UNIX and address[0] not in local:
            raise OSError('External networking is disabled in this browser fixture')
        return original_connect(self, address)

    def connect_ex(self, address):
        if self.family != socket.AF_UNIX and address[0] not in local:
            raise OSError('External networking is disabled in this browser fixture')
        return original_connect_ex(self, address)

    socket.getaddrinfo = resolve
    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
