#!/bin/bash

package_list="packages.list"
here=$(pwd)
vagrant_pkg_repo=$here/vagrant/cstbox-packages/

function update_package {
    pkg=$1

    cd ../$pkg
    echo "package $pkg:"

    arch_file=$(fab arch | grep "tar czf" | cut -d' ' -f 3)
    echo -e "\033[32m--> $arch_file \033[0m"
    cp -a $arch_file $vagrant_pkg_repo

    deb_file=$(fab build | grep "fakeroot dpkg" | cut -d' ' -f 5)
    echo -e "\033[32m--> $deb_file \033[0m"
    cp -a $deb_file $vagrant_pkg_repo

    cd - > /dev/null
}

if [ $# -eq 0 ] ; then
    while read pkg ; do
        [ -z "$pkg" ] && continue
        update_package $pkg
    done < $package_list
else
    for pkg in "$@"; do
        if grep $pkg $package_list -q ; then
            update_package $pkg
        else
            echo -e "\033[31m*** $pkg not in $package_list:\033[34m"
            cat $package_list
            echo -e "\033[0m"
        fi
    done
fi
