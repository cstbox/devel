#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import sys
import shutil
import argparse
import subprocess
import hashlib
import binascii

PACKAGES = None

STATUS_DIR_ROOT = './status'
DEPLOY_PATH_STORE = '.deploy_path'


class CTerm:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    WHITE = '\033[0;37m'
    HIRED = '\033[1;31m'
    HIGREEN = '\033[1;32m'
    HIYELLOW = '\033[1;33m'
    HIBLUE = '\033[1;34m'
    HIWHITE = '\033[1;37m'

    RESET = '\033[0m'

    HEADER = HIWHITE
    INFO = CYAN
    SUCCESS = GREEN
    WARNING = YELLOW
    FAIL = RED

    FORMAT = {
        'info': INFO + '[I] %s' + RESET,
        'success': SUCCESS + '[S] %s' + RESET,
        'warn': WARNING + '[W] %s' + RESET,
        'error': FAIL + '[E] %s' + RESET,
    }

    @classmethod
    def out(cls, msg, with_color=''):
        print(with_color + msg + cls.RESET)

    @classmethod
    def success(cls, msg):
        cls.out(cls.FORMAT['success'] % msg)

    @classmethod
    def error(cls, msg):
        cls.out(cls.FORMAT['error'] % msg)

    @classmethod
    def warn(cls, msg):
        cls.out(cls.FORMAT['warn'] % msg)

    @classmethod
    def info(cls, msg):
        cls.out(cls.FORMAT['info'] % msg)

    @classmethod
    def header(cls, title):
        cls.out('-'*10 + ' ' + title, with_color=cls.HEADER)


# just for pylint not complaining since these vars are dynamically created
CBX_GIT = CBX_DEPLOY_PATH = None

module = sys.modules[__name__]
try:
    for var_name in ('CBX_GIT', 'CBX_DEPLOY_PATH'):
        setattr(module, var_name, os.environ[var_name])

except KeyError as e:
    CTerm.error(
        "envionment variable %s is not defined" % e.message
    )
    sys.exit(1)

else:
    m = hashlib.md5()
    m.update(CBX_DEPLOY_PATH)
    STATUS_DIR = os.path.join(STATUS_DIR_ROOT, binascii.hexlify(m.digest()))


def do_init(args):
    CTerm.header('initializing')
    if not os.path.exists(STATUS_DIR):
        os.mkdir(STATUS_DIR)
        with file(os.path.join(STATUS_DIR, DEPLOY_PATH_STORE), 'wt') as f:
            f.write(CBX_DEPLOY_PATH)
        CTerm.success('status directory created')


def do_all(args):
    CTerm.header('deploying all packages')
    do_init(args)
    for package_name in PACKAGES:
        args.package = package_name
        _do_package(args)


def do_package(args):
    do_init(args)


def _do_package(args):
    CTerm.header("deploying package cstbox-%s" % args.package)

    package_root = os.path.join(CBX_GIT, args.package)
    if not os.path.exists(package_root):
        raise ValueError("package directory not found : %s" % package_root)

    package_link = os.path.join(package_root, "cstbox-%s.deb" %  args.package)

    status_file = os.path.join(STATUS_DIR, args.package)
    try:
        last_deployed = os.path.getmtime(status_file)
    except os.error:
        last_deployed = 0

    if not os.path.exists(package_link):
        CTerm.info('creating distribution package...')
        cwd = os.getcwd()
        try:
            os.chdir(package_root)
            subprocess.check_call("make dist", shell=True)

        except subprocess.CalledProcessError as e:
            raise Exception(
                "%s failed with return code %d" % (e.cmd, e.returncode)
            )

        finally:
            os.chdir(cwd)

    last_modified = os.path.getmtime(package_link)
    package_file = os.path.join(
        os.path.dirname(package_link),
        os.readlink(package_link)
    )

    if last_modified > last_deployed:
        CTerm.info('deploying distribution package...')
        subprocess.check_call(
            "rsync -Cav %s %s" % (package_file, CBX_DEPLOY_PATH),
            shell=True
        )

        subprocess.check_call("touch %s" % status_file, shell=True)

        CTerm.success('done')

    else:
        CTerm.success('no change since last deployed')


def do_clean(args):
    CTerm.header('cleaning')
    shutil.rmtree(STATUS_DIR, ignore_errors=True)
    CTerm.success('status directory deleted')


def do_status(args):
    STATUS_FORMAT = CTerm.WHITE + "%30s " + CTerm.GREEN + "%s" + CTerm.RESET
    HEADER_SEP = '-'*30 + ' ' + '-'*24
    HEADER_FORMAT = "%30s %s"
    try:
        CTerm.out(HEADER_FORMAT % ("Package", "Last deployed"), CTerm.WHITE)
        CTerm.out(HEADER_SEP, CTerm.WHITE)
        for name in sorted((fname for fname in os.listdir(STATUS_DIR) if fname != DEPLOY_PATH_STORE)):
            mtime = os.path.getmtime(os.path.join(STATUS_DIR, name))
            print(STATUS_FORMAT % (name, time.ctime(mtime)))
    except OSError:
        CTerm.warn("no status available")


def do_info(args):
    def label(s):
        print(CTerm.BLUE + s + ': ' + CTerm.RESET)

    def value(s):
        print('   ' + s)

    label("Deployment path ('>' = current")
    for name in os.listdir(STATUS_DIR_ROOT):
        _path = os.path.join(STATUS_DIR_ROOT, name)
        if os.path.isdir(_path):
            deploy_path_store = os.path.join(_path, DEPLOY_PATH_STORE)
            if os.path.exists(deploy_path_store):
                deploy_path = file(deploy_path_store, 'rt').readline()
                marker = '>' if deploy_path == CBX_DEPLOY_PATH else '-'
                value(marker + ' ' + deploy_path)
    label("Application packages list")
    for pname in sorted(PACKAGES):
        value(pname)
    print


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="CSTBox application optimized deployment tool."
    )
    parser.add_argument('-c', '--config',
                        default='packages.cfg',
                        help='application packages list'
                        )

    subparsers = parser.add_subparsers()

    parser_all = subparsers.add_parser('all')
    parser_all.set_defaults(handler=do_all)

    parser_package = subparsers.add_parser('package')
    parser_package.add_argument(
        'package',
        choices=PACKAGES
    )
    parser_package.set_defaults(handler=do_package)

    parser_init = subparsers.add_parser('init')
    parser_init.set_defaults(handler=do_init)

    parser_clean = subparsers.add_parser('clean')
    parser_clean.set_defaults(handler=do_clean)

    parser_status = subparsers.add_parser('status')
    parser_status.set_defaults(handler=do_status)

    parser_status = subparsers.add_parser('info')
    parser_status.set_defaults(handler=do_info)

    _args = parser.parse_args()

    if not os.path.exists(_args.config):
        CTerm.error("We are not at the right place : no file '%s' here." %
                    _args.config)
        sys.exit(2)

    try:
        with file(_args.config, 'rt') as _f:
            PACKAGES = [s for s in (
                s.strip() for s in _f.readlines()
            ) if not s.startswith('#')]

    except IOError as e:
        CTerm.error(e)
        sys.exit(1)

    else:
        try:
            _args.handler(_args)
        except Exception as e: #pylint: disable=W0703
            CTerm.error(e)
            sys.exit(1)

