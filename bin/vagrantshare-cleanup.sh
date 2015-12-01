#!/bin/bash

# Cleanups the Vagrant shared dir by removing obsolete archives and Debian packages

package_list="packages.list"
here=$(pwd)
vagrant_pkg_repo=$here/vagrant/cstbox-packages/

function cleanup_obsolete_files {
    pkg=$1
    ext=$2

    files=$(ls ${vagrant_pkg_repo}cstbox-${pkg}_*.$ext -t 2> /dev/null)
    [ $? == 0 ] || return

    latest=$(echo $files | cut -d' ' -f1)
    obsoletes=$(echo $files | cut -d' ' -f1 -s --complement)

    echo -e "\033[1;32m--> kept : $(basename $latest) \033[0m"
    if [ -n "$obsoletes" ] ; then
        rm $obsoletes

        list=""
        for f in $obsoletes; do
            list="$list$(basename $f) "
        done
        echo -e "\033[34m--> del. : $list \033[0m"
    fi
}

function cleanup_obsolete_package {
    pkg=$1

    echo "package $pkg:"
    cleanup_obsolete_files $pkg deb
    cleanup_obsolete_files $pkg tgz
}

if [ ! -f $package_list ] ; then
    echo -e "\033[31m*** $package_list file not found\033[34m"
    exit 1
fi

if [ $# -eq 0 ] ; then
    while read pkg ; do
        [ -z "$pkg" ] && continue
        cleanup_obsolete_package $pkg
    done < $package_list
else
    for pkg in "$@"; do
        if grep $pkg $package_list -q ; then
            cleanup_obsolete_package $pkg
        else
            echo -e "\033[31m*** $pkg not in $package_list:\033[34m"
            cat $package_list
            echo -e "\033[0m"
        fi
    done
fi
