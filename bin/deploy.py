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

    package_link = os.path.join(package_root, "cstbox-%s.deb" % args.package)

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
    print(CTerm.BLUE + 'Current target: ' + CTerm.RESET + CBX_DEPLOY_PATH)

    STATUS_FORMAT = CTerm.WHITE + "%30s %s%24s %s%24s" + CTerm.RESET
    HEADER_SEP = '-'*30 + ' ' + '-'*24 + ' ' + '-'*24
    HEADER_FORMAT = "%30s %24s %24s"
    try:
        CTerm.out(HEADER_FORMAT % ("Package", "Last updated", "Last deployed"), CTerm.WHITE)
        CTerm.out(HEADER_SEP, CTerm.WHITE)
        for name in sorted((fname for fname in os.listdir(STATUS_DIR) if fname != DEPLOY_PATH_STORE)):
            last_deployed = os.path.getmtime(os.path.join(STATUS_DIR, name))

            pkg_link = os.path.join(CBX_GIT, name, "cstbox-%s.deb" % name)
            if not os.path.exists(pkg_link):
                pkg_version = None
                pkg_col = CTerm.RED
                deploy_col = CTerm.BLUE
            else:
                pkg_file = os.readlink(pkg_link)
                pkg_version = os.path.getmtime(os.path.join(os.path.dirname(pkg_link), pkg_file))
                if pkg_version <= last_deployed:
                    pkg_col = CTerm.BLUE
                    deploy_col = CTerm.GREEN
                else:
                    deploy_col = pkg_col = CTerm.RED

            print(STATUS_FORMAT % (name, pkg_col, time.ctime(pkg_version) if pkg_version else 'n/a', deploy_col, time.ctime(last_deployed)))

    except OSError as err:
        CTerm.warn("no status available (%s)" % err)


def label(s):
    print(CTerm.BLUE + s + ': ' + CTerm.RESET)


def value(s):
    print('   ' + s + CTerm.RESET)


def _display_targets(menu=False):
    targets = []
    for name in os.listdir(STATUS_DIR_ROOT):
        _path = os.path.join(STATUS_DIR_ROOT, name)
        if os.path.isdir(_path):
            deploy_path_store = os.path.join(_path, DEPLOY_PATH_STORE)
            if os.path.exists(deploy_path_store):
                deploy_path = file(deploy_path_store, 'rt').readline()
                targets.append(deploy_path)
                if menu:
                    color = CTerm.WHITE if deploy_path == CBX_DEPLOY_PATH else CTerm.GREEN
                    marker = color + "[%2d]" % len(targets)
                else:
                    marker = '>' if deploy_path == CBX_DEPLOY_PATH else CTerm.GREEN + '-'
                value(marker + ' ' + deploy_path)

    return targets


def do_targets(args):
    label("Deployment targets (highlighted = current)")
    _display_targets()


def do_set_target(args):
    label("Deployment targets (highlighted = current)")
    targets = _display_targets(menu=True)
    user_input = raw_input("Select the id of the target to activate ([1-%d] or none to cancel) : " % len(targets)).strip()
    if len(user_input) == 0:
        CTerm.info("Current target left unchanged.")

    else:
        try:
            target_num = int(user_input)
            if not target_num - 1 in xrange(len(targets)):
                raise ValueError()
            CTerm.info('Execute the following statement at your bash prompt to change the deployment target : ')
            print('export CBX_DEPLOY_PATH=' + targets[target_num - 1])

        except ValueError:
            CTerm.error("Invalid reply.")


def do_packages(args):
    label("Application packages list")
    for pname in sorted(PACKAGES):
        value(pname)


def do_info(args):
    do_targets(args)
    do_packages(args)


def do_ls(args):
    for name in os.listdir(STATUS_DIR_ROOT):
        _path = os.path.join(STATUS_DIR_ROOT, name)
        if os.path.isdir(_path):
            deploy_path_store = os.path.join(_path, DEPLOY_PATH_STORE)
            if os.path.exists(deploy_path_store):
                deploy_path = file(deploy_path_store, 'rt').readline()
                print(CTerm.BLUE + name + CTerm.RESET + ' ' + deploy_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="CSTBox application optimized deployment tool."
    )
    parser.add_argument('-c', '--config',
                        default='packages.cfg',
                        help='application packages list'
                        )

    subparsers = parser.add_subparsers()

    parser_all = subparsers.add_parser('all',
                                       help='deploys all packages of the configuration')
    parser_all.set_defaults(handler=do_all)

    parser_package = subparsers.add_parser('package',
                                           help='deploys a single package')
    parser_package.add_argument(
        'package',
        choices=PACKAGES,
        help='name of the package to be deployed'
    )
    parser_package.set_defaults(handler=do_package)

    parser_packages = subparsers.add_parser('packages',
                                           help='displays the configuration packages list')
    parser_packages.set_defaults(handler=do_packages)

    parser_targets = subparsers.add_parser('targets',
                                           help='displays the list of know targets')
    parser_targets.set_defaults(handler=do_targets)

    parser_targets = subparsers.add_parser('target',
                                           help='changes the deployment target')
    parser_targets.set_defaults(handler=do_set_target)

    parser_init = subparsers.add_parser('init',
                                        help='initializes the context for the current deployment target')
    parser_init.set_defaults(handler=do_init)

    parser_clean = subparsers.add_parser('clean',
                                         help='deletes all status information for the current deployment target')
    parser_clean.set_defaults(handler=do_clean)

    parser_status = subparsers.add_parser('status',
                                          help="displays the deployment status of the current target")
    parser_status.set_defaults(handler=do_status)

    parser_status = subparsers.add_parser('ls',
                                          help="human list of status directories")
    parser_status.set_defaults(handler=do_ls)

    parser_status = subparsers.add_parser('info',
                                          help="displays information about the context")
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

