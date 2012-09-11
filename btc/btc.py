import re, os
import json, sys
import argparse
import fileinput
import collections
import utils
import atexit
from btclient import BTClient

def finish():
    try:
        sys.stdout.close()
    except:
        pass
    try:
        sys.stderr.close()
    except:
        pass

atexit.register(finish)

encoder = json.JSONEncoder(indent = 2)
decoder = json.JSONDecoder()

def error(msg, die=True):
    sys.stderr.write('%s: error: %s\n' % (os.path.basename(sys.argv[0]), msg))
    if die:
        exit(1)

def warning(msg):
    sys.stderr.write('%s: warning: %s\n' % (os.path.basename(sys.argv[0]), msg))

original_config = {}
config_file = os.path.join(os.getenv('HOME'), '.btc')
config = {}

if os.path.exists(config_file):
    _c = open(config_file, 'r')
    content = _c.read()
    if len(content.strip()) != 0:
        try:
            original_config = decoder.decode(content)
        except:
            msg = 'settings file parse error: %s' % config_file
            msg += '\n\ncontent is:\n%s' % content
            error(msg)
    _c.close()

config = dict(original_config)
default = {
    'host': '127.0.0.1',
    'port': 8080,
    'username': 'admin',
    'password': ''
}

for k in default:
    if k not in config:
        config[k] = default[k]

client = BTClient(decoder, config['host'], config['port'],
                  config['username'], config['password'])


def usage(commands):
    app = os.path.basename(sys.argv[0]).split(' ')[0]
    print 'usage: %s <command> [<args>]' % app
    print
    print 'Commands are:'
    for c in commands:
        if hasattr(commands[c], '_description'):
            desc = commands[c]._description
        else:
            desc = 'NO _description DEFINED FOR SUBCOMMAND'
        print '    %-10s: %s' % (c, desc)

def list_to_dict(l, key):
    d = {}
    for t in l:
        d[t[key]] = dict(t)
        del d[t[key]][key]
    return d

def dict_to_list(d, key):
    l = []
    for k in d:
        new = dict(d[k])
        new[key] = k
        l.append(new)
    return l

def cmp_to_key(mycmp):
    class K(object):
        def __init__(self, obj, *args):
            self.obj = obj
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0
        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0
        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0
        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0
        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0
        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
    return K

def cmp(a, b):
    a = a[0]
    b = b[0]
    l = ['name', 'hash', 'sid', 'fileid']
    if a == b:
        return 0
    elif a in l and b not in l:
        return -1
    elif b in l and a not in l:
        return 1
    elif a in l and b in l:
        return l.index(a) < l.index(b) and -1 or 1
    else:
        return a < b and -1 or 1

def ordered_dict(d1):
    vals = sorted([(k, d1[k]) for k in d1.keys()], key=cmp_to_key(cmp))
    d2 = collections.OrderedDict(vals)
    return d2

def main():
    commands = {}
    for fp in os.listdir(os.path.dirname(__file__)):
        match = re.match(r'btc_(.*)\.py', fp)

        if not match:
            continue

        name = match.group(1)
        module_name = 'btc_%s' % name
        module = getattr(__import__('btc.%s' % module_name), module_name)
        commands[name] = module

    if len(sys.argv) < 2:
        usage(commands)
        exit(1)

    if sys.argv[1] not in commands:
        error('no such command: %s' % sys.argv[1], False)
        print
        usage(commands)
        exit(1)

    module = commands[sys.argv[1]]
    sys.argv[0] += ' %s' % sys.argv[1]
    del sys.argv[1]

    try:
        module.main()
    except utils.HTTPError:
        verb = os.path.exists(config_file) and 'modify the' or 'create a'
        msg = 'connection failed, try to %s settings file\n' % verb
	msg += 'note: settings file is: %s\n' % config_file
        msg += 'note: curent settings are:\n'
        for k in config:
            msg += '    %8s: %s\n' % (k, config[k])
        error(msg[0:len(msg) - 1], die=False)
    except IOError:
        # might be better to put `raise` when debugging
        pass

    exit(0)

if __name__ == "__main__":
    main()