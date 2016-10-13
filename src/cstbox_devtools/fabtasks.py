#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import os
import re
import shutil
import glob
import subprocess

from fabric.api import local, put, sudo, cd, env, hosts, run, execute, lcd, task
from fabric.context_managers import settings
from fabric.utils import error, abort
from fabric.colors import blue, green
from fabric.decorators import with_settings

# from git_version import git_version
import setuptools_scm

__author__ = 'Eric Pascual - CSTB (eric.pascual@cstb.fr)'

_HERE = os.path.dirname(__file__)

REMOTE_TARGET_PACKAGES_DIR = "cstbox-packages/"

LOCAL_REPOS_ROOT = os.path.expanduser("~/cstbox-workspace/ppa/")
REPOS_PATH = {
}

env.use_ssh_config = True
env.no_agent = True
env.arch = env.get('arch', 'all')


def git_version():
    return setuptools_scm.get_version(version_scheme='post-release').split('+')[0]


def _find_project_root():
    while not os.path.isdir('.git'):
        os.chdir('..')
    root = os.path.abspath(os.getcwd())
    return root


def _get_package_name_and_version():
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
    return '%s_%s_%s.deb' % (name, version, env.arch)


def _get_package_arch_name():
    name, version = _get_package_name_and_version()
    return '%s_%s_%s.tgz' % (name, version, env.arch)


def _get_debian_control_path():
    return os.path.join(_find_project_root(), 'DEBIAN', 'control')


def _version_fields(version):
    fields = version.split('.')
    # add the build field if none
    if len(fields) < 4 and not fields[-1].isdigit():
        fields.insert(2, 0)
    return tuple((int(s) for s in fields[:3]))


def inc_version(version, inc_major=False, inc_minor=False, inc_build=True):
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
def version():
    print(git_version())


@task(aliases=["inc_patch", "inc_version_patch", "inc_version_build"])
def inc_build_num():
    """ Increase the build number in package version number """
    local('git tag -a -m "%(version_str)s" %(version_str)s' % {'version_str': inc_version(git_version())})


@task(alias="inc_minor")
def inc_version_minor():
    """ Increase the minor number in package version number """
    local('git tag -a -m "%(version_str)s" %(version_str)s' % {'version_str': inc_version(git_version(), inc_minor=True)})


@task(alias="inc_major")
def inc_version_major():
    """ Increase the major number in package version number """
    local('git tag -a -m "%(version_str)s" %(version_str)s' % {'version_str': inc_version(git_version(), inc_major=True)})


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
        file(control_path, 'wt').writelines(''.join(lines) % {
            'version': new_version,
            'arch': env.arch
        })
        print(green('%s version field updated to "%s"' % (control_path, new_version)))
        print(green('%s arch field set to "%s"' % (control_path, env.arch)))


@task(alias="deb")
def make_deb():
    """ Generates the Debian package """
    with lcd(_find_project_root()):
        if os.path.exists(os.path.join('DEBIAN', 'control.template')):
            execute(make_deb_control)
        else:
            execute(update_deb_version)

        execute(update__version__)
        local('ARCH=%s make clean_build dist' % env.arch)


@task(alias="arch")
def make_arch():
    """ Generates a deployable archive of the package """
    new_version = git_version()
    with lcd(_find_project_root()):
        execute(update__version__)
        local('VERSION=%s make clean_build arch' % new_version)


@task(alias="wheel")
def make_wheel():
    """ Generates a wheel of the package """
    with lcd(_find_project_root()):
        local('python setup.py bdist_wheel')


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
def publish(to='vagrant', addit_copy_func=None):
    """ Copies the Debian package to a repository (parms: to=vagrant) """
    try:
        project_root = _find_project_root()
        pkg_fn = _get_package_file_name()

    except IOError:
        error('no Debian package defined for this component')

    else:
        pkg_fpath = os.path.join(project_root, 'dist', pkg_fn)
        if not os.path.isfile(pkg_fpath):
            pkg_fpath = os.path.join(project_root, pkg_fn)
            if not os.path.isfile(pkg_fpath):
                error('Debian package %s not yet generated' % pkg_fn)

        try:
            local('cp -a %s %s' % (pkg_fpath, REPOS_PATH[to]))
            if addit_copy_func:
                addit_copy_func(pkg_fpath, REPOS_PATH[to])
        except KeyError:
            error('repository "%s" does not exist' % to)


@task
def sign_deb():
    """ Signs the Debian package"""
    with lcd(_find_project_root()):
        pkg_fn = _get_package_file_name()
        if not os.path.exists(pkg_fn):
            pkg_fn = os.path.join('dist', pkg_fn)
        local('dpkg-sig -k cstbox --sign builder %s' % pkg_fn)


PPA_NAME = None
VISIBLE_ON_PUBLIC_SERVER = False
PPA_KEEP_MULTIPLE_VERSION = True

PPA_DIR_PATH = "/var/www/cstbox-ppa/"


@hosts('tydom')
@with_settings(user='root', password='root')
@task
def tydom_deploy():
    """ Deploys a package archive on a connected Tydom"""
    # local('scp -r lib/python/pycstbox/* root@tydom:/opt/cstbox/lib/python/pycstbox/')
    project_root = _find_project_root()
    arch_name = _get_package_arch_name()
    local('scp -r %s root@tydom:%s' % (os.path.join(project_root, arch_name), REMOTE_TARGET_PACKAGES_DIR))


def do_update_ppa(ppa_name=None, ppa_servers=None, addit_copy_func=None):
    """ Updates the PPA with the most recent package version"""
    if not ppa_name:
        abort("ppa_name not defined. Cannot proceed.")

    execute(publish, to='ppa', addit_copy_func=addit_copy_func)
    execute(sign_deb)
    with lcd(REPOS_PATH['ppa']):
        scanpkg_opt = '-m' if PPA_KEEP_MULTIPLE_VERSION else ''
        local('dpkg-scanpackages %s . /dev/null > Packages' % scanpkg_opt)
        local('gzip -9ck Packages > Packages.gz')
        local('apt-ftparchive release . > Release')
        local('gpg --yes -abs -u cstbox -o Release.gpg Release')
        local('chmod g-w Release* Packages*')

    if ppa_servers:
        for server in list(ppa_servers):
            if server in ('public', 'private'):
                with lcd(LOCAL_REPOS_ROOT):
                    cmde = './update-server-ppa.sh %s %s'
                    local(cmde % (ppa_name, server))
            else:
                abort('invalid server : %s' % server)


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
    execute(make_arch)
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


@task()
def deb_clean():
    """ Removes generated distributions but the latest one """
    project_root = _find_project_root()
    pkg_name, version = _get_package_name_and_version()
    pkg_re = re.compile(r'^%s_.+all.*' % pkg_name)
    last_version_root_name = os.path.splitext(_get_package_file_name())[0]
    print("Keeping latest version : " + last_version_root_name)
    cnt = 0
    for name in os.listdir(project_root):
        if pkg_re.match(name) and not name.startswith(last_version_root_name):
            cnt += 1
            abspath = os.path.join(project_root, name)
            if os.path.isdir(abspath):
                shutil.rmtree(abspath)
            else:
                os.remove(abspath)
    if cnt:
        print("... %d obsolete package(s) removed." % (cnt / 2))
    else:
        print("... no obsolete package found.")


@task(alias="updpkg")
def vagrant_updpkg():
    project_root = _find_project_root()
    vagrant_dir = os.path.join(project_root, 'vagrant')
    if not os.path.isdir(vagrant_dir):
        abort('no Vagrant environment defined')

    pkg_list_file = os.path.join(vagrant_dir, 'packages.list')
    if not os.path.isfile(pkg_list_file):
        abort('packages.list file not found')

    vagrant_pkgs_dir = os.path.join(vagrant_dir, 'cstbox-packages')
    print('clearing packages in %s...' % vagrant_pkgs_dir)
    for f in glob.glob(vagrant_pkgs_dir + '/*.deb'):
        os.path.join(vagrant_pkgs_dir, f)

    pkg_files_list = []
    with open(pkg_list_file) as fp:
        for rec in fp:
            rec = rec.strip()
            if not rec:
                continue

            pkg_name, version = (rec.strip() + '=*').split('=')[:2]
            print('retrieving package %s (version: %s)...' % (pkg_name, 'latest' if version == '*' else version))
            _, short_name = pkg_name.split('-', 1)
            src_dist_dir = os.path.join(os.path.dirname(project_root), short_name, 'dist')
            if version != '*':
                src_deb_path = os.path.join(src_dist_dir, "%s_%s_%s.deb" % (pkg_name, version, env.arch))
            else:
                src_deb_path = os.path.join(src_dist_dir, "%s.deb" % pkg_name)

            if os.path.exists(src_deb_path):
                subprocess.call('cp -aL %s %s' % (src_deb_path, vagrant_pkgs_dir), shell=True)
                pkg_files_list.append(os.path.basename(src_deb_path))
            else:
                abort('ERROR: package file not found (%s)' % src_deb_path)

    pkg_install_script = os.path.join(vagrant_dir, 'install-packages.sh')
    with open(pkg_install_script, 'w') as fp:
        fp.write("dpkg -i " + ' '.join(["/vagrant/cstbox-packages/" + p for p in pkg_files_list]) + '\n')

