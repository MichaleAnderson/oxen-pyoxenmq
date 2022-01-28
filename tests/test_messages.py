
from bmq import BMQ, Message, LogLevel, AuthLevel, Address
import random
import string
from datetime import datetime, timedelta
import time
import pytest


def echo(m: Message):
    return 'Hi!', m.data()


def ohce(m: Message):
    return [bytes(reversed(x)) for x in reversed(m.data())], '!iH'


@pytest.fixture(autouse=True)
def zmq_address():
    import os
    sock = './' + ''.join(random.choices(string.ascii_letters, k=20)) + '.sock'
    addr = 'ipc://' + sock
    yield addr
    os.remove(sock)


def make_bmqs(zmq_addr, start=True):
    bmq1 = BMQ(log_level=LogLevel.trace)

    addr = Address(zmq_addr, bmq1.pubkey)

    bmq1.listen(addr.zmq_address, curve=True)

    bmq1.add_category('cat', AuthLevel.none) \
        .add_request_command('echo', echo) \
        .add_request_command('ohce', ohce)

    bmq2 = BMQ(log_level=LogLevel.trace)

    if start:
        bmq1.start()
        bmq2.start()

    return bmq1, bmq2, addr


def test_requests(zmq_address):
    bmq1, bmq2, addr = make_bmqs(zmq_address)

    reply1, reply2 = None, None

    def on_reply1(r):
        nonlocal reply1
        reply1 = [x.tobytes().decode() for x in r]

    def on_reply2(r):
        nonlocal reply2
        reply2 = [x.tobytes().decode() for x in r]

    c1 = bmq2.connect_remote(addr)
    bmq2.request(c1, 'cat.echo', 'fee', 'fi', 'fo', 'fum', on_reply=on_reply1)
    bmq2.request(c1, 'cat.ohce', 'fee', 'fi', 'fo', 'fum', on_reply=on_reply2)

    timeout = datetime.now() + timedelta(seconds=0.5)
    while None in (reply1, reply2) and datetime.now() < timeout:
        time.sleep(0.01)

    assert reply1 == ['Hi!', 'fee', 'fi', 'fo', 'fum']
    assert reply2 == ['muf', 'of', 'if', 'eef', '!iH']


def test_request_future(zmq_address):
    bmq1, bmq2, addr = make_bmqs(zmq_address)
    c1 = bmq2.connect_remote(addr)

    reply3 = [x.decode() for x in bmq2.request_future(c1, 'cat.echo', 'xyz').get()]
    assert reply3 == ['Hi!', 'xyz']


def test_commands(zmq_address):
    bmq1, bmq2, addr = make_bmqs(zmq_address, start=False)

    val1, val2, val3 = None, None, None
    defer = None

    def cmd1(m):
        nonlocal val1
        val1 = ['CMD1 got'] + m.data()
        m.back("x.x", "asdf", b'\x00\x01\x02', "jkl;")

    def cmd2(m):
        nonlocal val2, defer
        val2 = ['CMD2 got'] + m.data()
        defer = m.later()

    def cmd_later(m):
        nonlocal defer, val3
        val3 = ['CMD-later got'] + m.data()

    bmq1.add_category("x", AuthLevel.none) \
        .add_command("y", cmd1) \
        .add_command("z", cmd_later)

    bmq2.add_category("x", AuthLevel.none) \
        .add_command("x", cmd2)

    bmq1.start()
    bmq2.start()
    c1 = bmq2.connect_remote(addr)
    bmq2.send(c1, 'x.y', b'\0', 'M', 'G')

    timeout = datetime.now() + timedelta(seconds=0.5)
    while None in (val1, val2) and datetime.now() < timeout:
        time.sleep(0.01)

    assert val1 == ['CMD1 got', b'\0', b'M', b'G']
    assert val2 == ['CMD2 got', b'asdf', b'\0\1\2', b'jkl;']
    assert val3 is None
    assert defer is not None

    defer.back("x.z", "cool")
    timeout = datetime.now() + timedelta(seconds=0.5)
    while val3 is None and datetime.now() < timeout:
        time.sleep(0.01)
    assert val3 == ['CMD-later got', b'cool']

