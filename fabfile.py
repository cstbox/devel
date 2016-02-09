#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

import os
from fabric.api import local, put, sudo, cd, env, hosts, run, execute, lcd, task
from fabric.utils import error, abort
from fabric.colors import blue, green
from fabric.context_managers import settings
from fabric.decorators import with_settings
from fabric.network import ssh
from fabtools.vagrant import vagrant
from git_version import git_version

__author__ = 'Eric Pascual - CSTB (eric.pascual@cstb.fr)'

_HERE = os.path.dirname(__file__)

REMOTE_TARGET_PACKAGES_DIR = "cstbox-packages/"

REPOS_PATH = {
    'dropbox': os.path.expanduser("~/Dropbox-private/Dropbox/cstbox/"),
    #'ppa': os.path.expanduser("~/cstbox-workspace/ppa/"),
    'ppa': os.path.expanduser("~/Dropbox-private/Dropbox/cstbox-apt/"),
    'vagrant': os.path.join("vagrant", REMOTE_TARGET_PACKAGES_DIR),
    'vagrant.tydom': os.path.join(_HERE, "app-tydom", "vagrant", REMOTE_TARGET_PACKAGES_DIR),
    'vagrant.deltadore': os.path.join(_HERE, "ext-deltadore", "vagrant", REMOTE_TARGET_PACKAGES_DIR),
    'vagrant.wsfeed': os.path.join(_HERE, "ext-wsfeed", "vagrant", REMOTE_TARGET_PACKAGES_DIR),
}


# ssh.util.log_to_file("paramiko.log", 10)
env.use_ssh_config = True
env.no_agent = True
env.hosts = ['cbx-home']


def _find_project_root():
    while not os.path.isdir('.git'):
        os.chdir('..')
    root = os.path.abspath(os.getcwd())
    return root


def _get_package_name_and_version():
    name = version = None
    project_root = _find_project_root()

    deb_control = os.path.join(project_root, 'DEBIAN/control.template')
    if not os.path.exists(deb_control):
        deb_control = os.path.join(project_root, 'DEBIAN/control')
        if not os.path.exists(deb_control):
            abort('cannot find DEBIAN control or control.template file')

    # look for package name in the control file
    name = None
    for line in file(deb_control):
        key, value = line.split(':')
        key = key.strip()
        if key == 'Package':
            name = value.strip()
            break
    if not name:
        abort('cannot find package name in DEBIAN control or control.template file')

    # get the current git version
    version = git_version()

    return name, version


def _get_package_file_name():
    name, version = _get_package_name_and_version()
    return '%s_%s_all.deb' % (name, version)


def _get_package_arch_name():
    name, version = _get_package_name_and_version()
    return '%s_%s_all.tgz' % (name, version)


def _get_debian_control_path():
    return os.path.join(_find_project_root(), 'DEBIAN', 'control')


def _version_fields(version):
    fields = version.split('.')
    # add the build field if none
    if len(fields) < 4 and not fields[-1].isdigit():
        fields.insert(2, 0)
    return tuple((int(s) for s in fields[:3]))


def inc_version(version, inc_major=False, inc_minor=False, inc_build=True):
    name, version = _get_package_name_and_version()
    major, minor, build = _version_fields(version)
    if inc_major:
        major += 1
        minor = build = 0
    elif inc_minor:
        minor += 1
        build = 0
    elif inc_build:
        build += 1
    else:
        return version

    return '.'.join((str(n) for n in (major, minor, build)))


@task
def inc_version_build():
    """ Increase the build number in package version number """
    name, version = _get_package_name_and_version()
    local('git tag -a -m "%(version_str)s" %(version_str)s' % {'version_str': inc_version(version)})


@task
def inc_version_minor():
    """ Increase the minor number in package version number """
    name, version = _get_package_name_and_version()
    local('git tag -a -m "%(version_str)s" %(version_str)s' % {'version_str': inc_version(version, inc_minor=True)})


@task
def inc_version_major():
    """ Increase the major number in package version number """
    name, version = _get_package_name_and_version()
    local('git tag -a -m "%(version_str)s" %(version_str)s' % {'version_str': inc_version(version, inc_major=True)})


@task
def update_deb_version():
    """ Updates the version field in the DEBIAN/control file (deprecated) """
    project_root = _find_project_root()

    new_version = git_version()

    control_path = os.path.join(project_root, 'DEBIAN/control')
    lines = file(control_path).readlines()
    for num, line in enumerate(lines):
        if line.startswith('Version:'):
            tag, current_version = line.strip().split(' ', 1)
            if new_version != current_version:
                lines[num] = ' '.join((tag, new_version)) + '\n'
                os.rename(control_path, '%s-%s.bak' % (control_path, current_version))
                file(control_path, 'wt').writelines(lines)
                print(green('version changed to %s' % new_version))
                return

    print(blue('no version change'))


@task
def update__version__():
    """ Updates the __version__.py file if it exists """
    project_root = _find_project_root()
    try:
        python_pkg_version_path = file(os.path.join(project_root, 'VERSION_PY_PATH')).readlines()[0].strip()
        version = git_version()
        version_module_path = os.path.join(project_root, python_pkg_version_path, '__version__.py')
        file(version_module_path, 'wt').write('version = "%s"\n' % version)

    except IOError:
        pass


@task
def make_deb_control():
    """ Generates de DEBIAN/control file """
    project_root = _find_project_root()

    try:
        new_version = git_version()
    except ValueError:
        print(error("cannot determine the version number. Did you create a git tag for it ?"))
        abort()
    else:
        control_path = os.path.join(project_root, 'DEBIAN', 'control')
        template_path = control_path + '.template'
        lines = file(template_path).readlines()
        file(control_path, 'wt').writelines(''.join(lines) % {'version': new_version})
        print(green('%s version field updated to "%s"' % (control_path, new_version)))


@task
def build_deb():
    """ Generates the Debian package """
    with lcd(_find_project_root()):
        if os.path.exists(os.path.join('DEBIAN', 'control.template')):
            execute(make_deb_control)
        else:
            execute(update_deb_version)

        execute(update__version__)
        local('make clean_build  dist')


@task
def build_arch():
    """ Generates a deployable archive of the package """
    new_version = git_version()
    with lcd(_find_project_root()):
        execute(update__version__)
        local('VERSION=%s make clean_build arch' % new_version)


@task
def deploy():
    """ Deploys the Debian package to the target """
    put(_get_package_file_name(), REMOTE_TARGET_PACKAGES_DIR)


@task
def install(name=''):
    """ Remotely installs the Debian package (parms: name=<current one>)"""
    pkg_name = name or _get_package_file_name()
    pkg_dir_prefix = '/vagrant' if env.user == 'vagrant' else ''
    sudo('service cstbox stop')
    sudo('dpkg -i %s' % os.path.join(pkg_dir_prefix, REMOTE_TARGET_PACKAGES_DIR, pkg_name))
    sudo('service cstbox start')


@task
def publish(to='vagrant'):
    """ Copies the Debian package to a repository (parms: to=vagrant) """
    try:
        project_root = _find_project_root()
        pkg_fn = os.path.join(project_root, _get_package_file_name())
    except IOError:
        error('no Debian package defined for this component')
    else:
        if os.path.isfile(pkg_fn):
            try:
                local('cp -a %s %s' % (pkg_fn, REPOS_PATH[to]))
            except KeyError:
                error('repository "%s" does not exist' % to)
        else:
            error('Debian package %s not yet generated' % pkg_fn)


@task
def sign_deb():
    """ Signs the Debian package"""
    with lcd(_find_project_root()):
        local('dpkg-sig -k cstbox --sign builder %s' % _get_package_file_name())


PPA_KEEP_MULTIPLE_VERSION = False


@task
def update_ppa():
    """ Updates the PPA with the most recent package version"""
    execute(publish, to='ppa')
    execute(sign_deb)
    with lcd(REPOS_PATH['ppa']):
        local('dpkg-scanpackages %s . /dev/null > Packages' % ('-m' if PPA_KEEP_MULTIPLE_VERSION else ''))
        local('bzip2 -kf Packages')
        local('apt-ftparchive release . > Release')
        local('gpg --yes -abs -u cstbox -o Release.gpg Release')


@hosts('tydom')
@with_settings(user='root', password='root')
@task
def tydom_deploy():
    """ Deploys a package archive on a connected Tydom"""
    # local('scp -r lib/python/pycstbox/* root@tydom:/opt/cstbox/lib/python/pycstbox/')
    project_root = _find_project_root()
    arch_name = _get_package_arch_name()
    local('scp -r %s root@tydom:%s' % (os.path.join(project_root, arch_name), REMOTE_TARGET_PACKAGES_DIR))


@hosts('tydom')
@with_settings(user='root', password='root')
@task
def tydom_install():
    """ Installs a package on a connected Tydom"""
    user_home = '/root' if env.user == 'root' else os.path.join('/home', env.user)
    arch_name = _get_package_arch_name()
    # with cd("/"):
    #     run('tar xf %s' % os.path.join(user_home, REMOTE_TARGET_PACKAGES_DIR, arch_name))
    with cd(os.path.join(user_home, REMOTE_TARGET_PACKAGES_DIR)):
        run('./install.sh ' + arch_name)


@hosts('tydom')
@with_settings(user='root', password='root')
@task
def tydom_cbx_restart():
    """ Restarts CSTBox services on a connected Tydom"""
    run("/etc/init.d/cstbox stop")
    time.sleep(5)
    run("/etc/init.d/cstbox start")


@task
def tydom_all():
    """ Builds, deploys and installs a package on a connected Tydom """
    execute(build_arch)
    execute(tydom_deploy)
    execute(tydom_install)
    execute(tydom_cbx_restart)


DOCUMENTATION_SUBDIRS = ['./docs', './doc']


@task
def doc(output_format='html', clean=False):
    """ Generates the package documentation. (parms: output_format=html, clean=False) """
    doc_subdir = None
    for d in DOCUMENTATION_SUBDIRS:
        if os.path.isdir(d):
            doc_subdir = d
            break

    if not doc_subdir:
        abort('documentation subdir not found')

    with lcd(doc_subdir):
        clean_opt = 'clean' if clean else ''
        local("make %s %s" % (clean_opt, output_format))
