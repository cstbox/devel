#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Eric Pascual - CSTB (eric.pascual@cstb.fr)'

import sys
import os
import argparse
import subprocess
import time


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

    HEADER = WHITE
    BANNER = WHITE
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
        cls.out(title.capitalize(), with_color=cls.HEADER)

    @classmethod
    def banner(cls, title):
        cls.out('-'*10 + ' ' + title, with_color=cls.BANNER)

    @classmethod
    def label(cls, s):
        print(CTerm.BLUE + s + ': ' + CTerm.RESET)

    @classmethod
    def value(cls, s):
        print('   ' + s + CTerm.RESET)


TARGETS_ROOT = './targets'
TARGET_STATUS_SUBDIR = 'status'
TARGET_MIRROR_SUBDIR = 'mirror'
TARGET_MIRROR_PKG = TARGET_MIRROR_SUBDIR + '/pkg'
TARGET_MIRROR_CFG = TARGET_MIRROR_SUBDIR + '/cfg'
DEPLOY_PATH_STORE = '.deploy_path'

PACKAGES_CONFIG = "packages.cfg"

_packages = None

_directory = None
_targets = None
_current_target = None

# just for pylint not complaining since these vars are dynamically created
CBX_GIT = CBX_DEPLOY_PATH = None


def _update_directory():
    global _directory, _targets, _current_target

    _directory = {}
    for name in os.listdir(TARGETS_ROOT):
        _path = os.path.join(TARGETS_ROOT, name)
        if os.path.isdir(_path):
            deploy_path_store = os.path.join(_path, DEPLOY_PATH_STORE)
            if os.path.exists(deploy_path_store):
                deploy_path = file(deploy_path_store, 'rt').readline()
                _directory[name] = deploy_path
                if deploy_path == CBX_DEPLOY_PATH:
                    _current_target = name

    _targets = sorted(_directory.keys())


def do_all(args):
    CTerm.header('deploying all packages...')
    for package in _packages:
        CTerm.banner("cstbox-" + package)
        _deploy_package(package)


def do_package(args):
    CTerm.header("deploying package cstbox-%s..." % args.package)
    _deploy_package(args.package)


def _deploy_package(package):
    package_src_dir = os.path.join(CBX_GIT, package)
    if not os.path.exists(package_src_dir):
        raise ValueError("package directory not found : %s" % package_src_dir)

    package_link = os.path.join(package_src_dir, "cstbox-%s.deb" % package)

    target_root = os.path.join(TARGETS_ROOT, _current_target)
    status_file = os.path.join(target_root, TARGET_STATUS_SUBDIR, package)
    try:
        last_deployed = os.path.getmtime(status_file)
    except os.error:
        last_deployed = 0

    if not os.path.exists(package_link):
        CTerm.info('creating distribution package...')
        cwd = os.getcwd()
        try:
            os.chdir(package_src_dir)
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
            "rsync -av %s %s" % (package_file, CBX_DEPLOY_PATH),
            shell=True
        )

        subprocess.check_call("touch %s" % status_file, shell=True)
        subprocess.check_call(
            "cp -a %s %s" % (package_file, os.path.join(target_root, TARGET_MIRROR_PKG)),
            shell=True
        )

        CTerm.success('done')

    else:
        CTerm.success('no change since last deployed')


def do_list_packages(args):
    CTerm.header("Application packages list")
    for pname in sorted(_packages):
        CTerm.value(CTerm.GREEN + '- ' + pname)


def _display_targets(menu=False):
    for num, name, deploy_path in [(i+1, name, _directory[name]) for i, name in enumerate(_targets)]:
        if menu:
            color = CTerm.HIWHITE if deploy_path == CBX_DEPLOY_PATH else CTerm.GREEN
            marker = color + "[%2d]" % num
        else:
            marker = CTerm.HIWHITE + '*' if deploy_path == CBX_DEPLOY_PATH else CTerm.GREEN + '-'
        CTerm.value(marker + ' ' + name.ljust(20) + ' -> ' + CTerm.BLUE + deploy_path)


def do_targets(args):
    CTerm.header("Deployment targets " + CTerm.BLUE + "(highlighted = current)")
    _display_targets(menu=True)
    user_input = raw_input(
        "Select the id of the target to activate ([1-%d]) or hit Enter to keep the current one : " % len(_targets)
    ).strip()
    if user_input:
        try:
            target_num = int(user_input)
            if not target_num - 1 in xrange(len(_targets)):
                raise ValueError()
            CTerm.info('Execute the following statement at your bash prompt to change the deployment target : ')
            print('export CBX_DEPLOY_PATH=' + _directory[_targets[target_num - 1]])

        except ValueError:
            CTerm.error("Invalid reply.")


def do_create_target(args):
    CTerm.banner('initializing...')
    root_subdir = os.path.join(TARGETS_ROOT, args.target_name)
    if not os.path.exists(root_subdir):
        os.mkdir(root_subdir)
        for d in (TARGET_STATUS_SUBDIR, TARGET_MIRROR_CFG, TARGET_MIRROR_PKG):
            os.makedirs(os.path.join(root_subdir, d))
        with file(os.path.join(root_subdir, DEPLOY_PATH_STORE), 'wt') as f:
            f.write(args.deploy_path)
        CTerm.success('target context created.')
        _update_directory()

    else:
        CTerm.warn("target '%s' already exists" % args.target_name)


def do_clean(args):
    CTerm.header('cleaning statuses...')
    path = os.path.join(TARGETS_ROOT, _current_target, TARGET_STATUS_SUBDIR)
    for f in os.listdir(path):
        os.remove(os.path.join(path, f))
    CTerm.success('status cleared')


def do_status(args):
    print(
        CTerm.BLUE + 'Current target : ' +
        CTerm.RESET + _current_target +
        CTerm.BLUE + ' -> ' + CTerm.GREEN + CBX_DEPLOY_PATH +
        CTerm.RESET
    )

    STATUS_FORMAT = CTerm.WHITE + "%30s %s%24s %s%24s" + CTerm.RESET
    HEADER_SEP = '-'*30 + ' ' + '-'*24 + ' ' + '-'*24
    HEADER_FORMAT = "%30s %24s %24s"
    try:
        CTerm.out(HEADER_FORMAT % ("Package", "Last updated", "Last deployed"), CTerm.WHITE)
        CTerm.out(HEADER_SEP, CTerm.WHITE)
        status_dir = os.path.join(TARGETS_ROOT, _current_target, TARGET_STATUS_SUBDIR)
        for name in sorted((fname for fname in os.listdir(status_dir) if fname != DEPLOY_PATH_STORE)):
            last_deployed = os.path.getmtime(os.path.join(status_dir, name))

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

            print(STATUS_FORMAT % (
                name,
                pkg_col,
                time.ctime(pkg_version) if pkg_version else 'n/a', deploy_col, time.ctime(last_deployed)
            ))

    except OSError as err:
        CTerm.warn("no status available (%s)" % err)


def li(s, hi=False):
    CTerm.out('  - ' + s, with_color=CTerm.HIWHITE if hi else CTerm.GREEN)


def do_info(args):
    CTerm.header("Available targets")
    for target in _targets:
        li(target, hi=(target == _current_target))

    CTerm.header("Application packages list")
    for pname in _packages:
        li(pname)


def do_mirror(args):
    CTerm.header("Retrieving target version of files...")
    if not any((args.mirror_all, args.mirror_pkg, args.mirror_cfg)):
        args.mirror_pkg = True
    elif args.mirror_all:
        args.mirror_pkg = args.mirror_cfg = True

    target_root = os.path.join(TARGETS_ROOT, _current_target)

    if args.mirror_pkg:
        CTerm.banner('packages')
        src = os.path.join(CBX_DEPLOY_PATH, '*')
        dst = os.path.join(target_root, TARGET_MIRROR_PKG)

        subprocess.check_call(
            "rsync -av %s %s" % (src, dst),
            shell=True
        )

    if args.mirror_cfg:
        CTerm.banner('configuration files')
        if ':' in CBX_DEPLOY_PATH:
            host, _ = CBX_DEPLOY_PATH.split(':')
            src = host + ':/etc/cstbox'
            dst = os.path.join(target_root, TARGET_MIRROR_CFG)
            subprocess.check_call(
                "rsync -arv %s %s" % (src, dst),
                shell=True
            )

        else:
            CTerm.error('cannot be done for local targets')


if __name__ == '__main__':
    if not os.path.exists(PACKAGES_CONFIG):
        CTerm.error("We are not at the right place : no file '%s' found in this directory." %
                    PACKAGES_CONFIG)
        sys.exit(2)

    try:
        with file(PACKAGES_CONFIG, 'rt') as _f:
            _packages = [s for s in (
                s.strip() for s in _f.readlines()
            ) if not s.startswith('#')]

    except IOError as e:
        CTerm.error(e)
        sys.exit(1)

    module = sys.modules[__name__]
    try:
        for var_name in ('CBX_GIT', 'CBX_DEPLOY_PATH'):
            setattr(module, var_name, os.environ[var_name])

    except KeyError as e:
        CTerm.error(
            "environment variable %s is not defined" % e.message
        )
        sys.exit(1)

    else:
        _update_directory()

    parser = argparse.ArgumentParser(
        description="CSTBox application optimized deployment tool."
    )
    subparsers = parser.add_subparsers(
        title='sub-commands'
    )

    def _target_name_type(s):
        import re
        if re.match(r'[a-zA-Z][a-zA-Z0-9_-]*', s):
            return s
        else:
            raise argparse.ArgumentTypeError()

    commands = {
        'all': (
            {
                'help': 'deploys all packages of the configuration'
            },
            None,
            do_all
        ),
        'package': (
            {
                'help': 'deploys a single package'
            },
            {
                'package': {
                    'metavar': 'PACKAGE_NAME',
                    'choices': _packages,
                    'help': 'name of the package to be deployed'
                }
            },
            do_package
        ),
        'packages': (
            {
                'help': 'displays the configuration packages list'
            },
            None,
            do_list_packages
        ),
        'targets': (
            {
                'help': 'displays the list of know targets, with the option to change current one'
            },
            None,
            do_targets
        ),
        'new': (
            {
                'help': 'initializes the context for a new deployment target'
            },
            {
                'target_name': {
                    'metavar': 'TARGET_NAME',
                    'help': 'symbolic name of the target',
                    'type': _target_name_type
                },
                'deploy_path': {
                    'metavar': 'DEPLOY_PATH',
                    'help': 'target deployment path (local or rsync/scp remote)'
                }
            },
            do_create_target
        ),
        'clean': (
            {
                'help': 'deletes all status information for the current deployment target'
            },
            None,
            do_clean
        ),
        'status': (
            {
                'help': "displays the deployment status of the current target"
            },
            None,
            do_status
        ),
        'info': (
            {
                'help': "displays information about the context"
            },
            None,
            do_info
        ),
        'mirror': (
            {
                'help': "mirrors locally the current version of files present on the target"
            },
            {
                '-c': {
                    'help': "mirror configuration files",
                    'dest': 'mirror_cfg',
                    'action': 'store_true'
                },
                '-p': {
                    'help': "mirror packages files",
                    'dest': 'mirror_pkg',
                    'action': 'store_true'
                },
                '-A': {
                    'help': "mirror all (same as -c -p)",
                    'dest': 'mirror_all',
                    'action': 'store_true'
                }
            },
            do_mirror
        )
    }

    for command in sorted(commands.keys()):
        cmd_kwargs, cmd_opts, cmd_handler = commands[command]
        sub_parser = subparsers.add_parser(
            command,
            **cmd_kwargs
        )
        if cmd_opts:
            for sub_opt, sub_opt_kwargs in cmd_opts.iteritems():
                sub_parser.add_argument(sub_opt, **sub_opt_kwargs)
        sub_parser.set_defaults(handler=cmd_handler)

    _args = parser.parse_args()

    try:
        if not os.path.exists(TARGETS_ROOT):
            os.mkdir(TARGETS_ROOT)

        _args.handler(_args)
    except Exception as e: #pylint: disable=W0703
        CTerm.error(e)
        sys.exit(1)



