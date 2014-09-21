# Shared parts for CSTBox components Makefile writing

# DON'T MODIFY THIS
PYTHON_VERSION=2.7

# author = Eric PASCUAL - CSTB (eric.pascual@cstb.fr)
# copyright = Copyright (c) 2013 CSTB
# vcsid = $Id$
# version = 1.0.0

ifndef MODULE_NAME
$(error MODULE_NAME variable is not defined)
endif

VERSION?=$(shell grep -e '^Version:' DEBIAN/control | cut -d' ' -f2 | tr -d [:blank:])

DEBPKG_NAME?=cstbox-$(MODULE_NAME)_$(VERSION)_all

# version status (stable or not)
STABLE?=1
ifeq ($(STABLE), 1)
SUFFIX=
else
SUFFIX=-unstable
endif

# build directory location
BUILD_DIR=$(DEBPKG_NAME)

# Specification of the default locations where the packaged material should be picked
# from. These variables can be overidden when invoking the make command if you choose 
# to layout your workspace differently than the Git one.
#
# - CSTBox libraries (Python, init,...)
LIB_FROM?=./lib
# - CSTBox bin scripts
BIN_FROM?=./bin
# - CSTBox configuration files
ETC_FROM?=./res/etc
# - CSTBox init.d scripts
INIT_D_FROM?=$(ETC_FROM)/init.d

# Specification of the locations where the various parts are installed on the 
# target system.

# 1/ CSTBox specific

# - root of the CSTBox framework file system
CSTBOX_INSTALL_DIR=opt/cstbox
# - root of CSTBox configuration files
ETC_CSTBOX_INSTALL_DIR=etc/cstbox

# 2/ System related

# - location of init scripts
INIT_D_INSTALL_DIR=etc/init.d
# - location of system profile extensions
PROFILE_D_INSTALL_DIR=etc/profile.d
# - location of per package logrotate settings
LOGROTATE_D_INSTALL_DIR=etc/logrotate.d
# - location of non CSTBox Python packages
#   There are 2 options here:
#   - install them under the CSTBox area
#   - install them in the Python system wide location
#   Both options will work the same, the first one having the advantage to leave
#   system installation untouched, and is thus seleted by default.
#   CAUTION: check that the path used here is included in the PYTHONPATH setting
#            contained in /etc/cstbox/setenv
SUPPORT_PACKAGES_INSTALL_DIR=$(CSTBOX_INSTALL_DIR)/deps/python
# Uncomment next line to install external Python dependencies in the system wide location
#SUPPORT_PACKAGES_INSTALL_DIR=usr/lib/python$(PYTHON_VERSION)/dist-packages

# Computed locations

# - CSTBox Python package directory
CSTBOX_PACKAGES_INSTALL_DIR=$(CSTBOX_INSTALL_DIR)/lib/python/
# - CSTBox Java archives
CSTBOX_JARS_INSTALL_DIR=$(CSTBOX_INSTALL_DIR)/lib/java/
# - CSTBox binaries directory
CSTBOX_BINARIES_INSTALL_DIR=$(CSTBOX_INSTALL_DIR)/bin

#RSYNC_VERBOSE=-v
RSYNC=rsync -Ca --prune-empty-dirs $(RSYNC_VERBOSE)

rm_devel_file = \rm $(BUILD_DIR)/$(CSTBOX_PACKAGES_INSTALL_DIR)/pycstbox/$(1)

dist: prepare
	@echo '------ creating Debian package...'
	PKG=$(DEBPKG_NAME)$(SUFFIX).deb
	fakeroot dpkg --build $(BUILD_DIR) $(PKG) 

prepare: i18n make_build_dir make_extra_dirs copy_dpkg_build_files copy_files 

i18n: 
	@echo '------ compiling message files...'
	find . -name "*.po" -exec bash -c 'msgfmt $$1 -o $${1/.po/.mo}' - {} $\\;

css:
	@echo '----- compiling SASS files...'
	find . -name "*.scss" -exec bash -c 'sass $$1 -o $${1/.po/.mo}' - {} $\\;

make_build_dir:
	@echo '------ creating dist build directories...'
	mkdir -p $(BUILD_DIR)

make_extra_dirs:
# overriden by Makefiles to add their own directories if needed

copy_files:
# CSTBox module Makefiles must define the copy_files rule and specify what 
# must be copied by assembling pre-defined rules as dependencies. 
# If no action other than pre-defined ones is needed, the rule can left empty. 
# It some other copy or action is needed, just put them in the rule content.
#
# Note that DEBIAN package stuff is already included in the 
# prepare phase definition.
#
# Ex:
# copy_files: copy_python_files copy_etc_files

copy_dpkg_build_files:
	@echo '------ copying dpkg control files...'
	$(RSYNC) DEBIAN $(BUILD_DIR)

copy_bin_files:
	@echo '------ copying CSTBox scripts and binaries...'
	mkdir -p \
	    $(BUILD_DIR)/$(CSTBOX_INSTALL_DIR)/bin 
# filter detail:
# - -s_*/.* : exclude all hidden files from being sent wherever they are
	$(RSYNC) \
	    --filter "-s_*/.*" \
	    $(BIN_FROM)/ $(BUILD_DIR)/$(CSTBOX_INSTALL_DIR)/bin

copy_python_files:
	@echo '------ copying Python component files ...'
	mkdir -p \
	    $(BUILD_DIR)/$(CSTBOX_PACKAGES_INSTALL_DIR) 
# filter detail:
# - -s */.* : exclude all hidden files from being sent wherever they are
# - -s */attic : exclude deprecated stuff (stored in 'attic' directories)
	$(RSYNC) \
	    --filter "-s */.*" \
	    --filter "-s */attic" \
	    --include "*/" \
	    --include "*.py" \
	    --include "*.html" \
	    --include "*.html" \
	    --include "*.js" \
	    --include "*.css" \
	    --include "*.png" \
	    --include "*.jpg" \
	    --include "*.jpeg" \
	    --include "*.gif" \
	    --include "*.mo" \
	    --include "MANIFEST" \
	    --exclude "*" \
	    $(LIB_FROM)/python/pycstbox $(BUILD_DIR)/$(CSTBOX_PACKAGES_INSTALL_DIR)

# remove the dummy root level __init__.py for packages other than core
#
# This file is here so that IDEs and tools can resolve the names when an extension
# package is manipulated outside the global pyCSTBox library. It must not be copied in 
# the distribution package, otherwise it will override the pyCSTBox library one and
# break lots of things, since this one is NOT empty)
#
# NOTE: it would be cleaner to find a way to exclude it from the above rsync, but I failed :/
#       Anyway the hereafter "if" would be here even in this case, since required for adding
#       the core package __init__ module.
	@if [ "$(MODULE_NAME)" != "core" ] ; then \
	    echo "------ removing 'dev tools compliance' __init__.py" ;\
	    \rm -f $(BUILD_DIR)/$(CSTBOX_PACKAGES_INSTALL_DIR)/pycstbox/__init__.py ;\
	fi

copy_python_support_pkgs:
	@echo '------ copying additional Python support packages...'
	mkdir -p \
	    $(BUILD_DIR)/$(SUPPORT_PACKAGES_INSTALL_DIR) 
	$(RSYNC) \
	    --filter "-s_*/.*" \
	    $(LIB_FROM)/python/deps/ $(BUILD_DIR)/$(SUPPORT_PACKAGES_INSTALL_DIR)

copy_jar_files:
	@echo '------ copying Java component files ...'
	mkdir -p \
	    $(BUILD_DIR)/$(CSTBOX_JARS_INSTALL_DIR) 
# filter detail:
# - -s_*/.* : exclude all hidden files from being sent wherever they are
# - -s_*/attic : exclude deprecated stuff (stored in 'attic' directories)
	$(RSYNC) \
	    --filter "-s_*/.*" \
	    --filter "-s_*/attic" \
	    --include "*/" \
	    --include "*.jar" \
	    --exclude "*" \
	    $(LIB_FROM)/java/ $(BUILD_DIR)/$(CSTBOX_JARS_INSTALL_DIR)

copy_devices_metadata_files:
	@echo '------ copying devices metadata files ...'
	mkdir -p \
	    $(BUILD_DIR)/$(CSTBOX_PACKAGES_INSTALL_DIR) 
# filter detail:
# - -s_*/.* : exclude all hidden files from being sent wherever they are
# - -s_*/attic : exclude deprecated stuff (stored in 'attic' directories)
	$(RSYNC) \
	    --filter "-s_*/.*" \
	    --filter "-s_*/attic" \
	    --include "devcfg.d/**/*" \
	    --include "devcfg.d/*" \
	    $(LIB_FROM)/python/pycstbox $(BUILD_DIR)/$(CSTBOX_PACKAGES_INSTALL_DIR)


copy_init_shared_files:
	@echo '------ copying init scripts shared library...'
	mkdir -p \
	    $(BUILD_DIR)/$(CSTBOX_INSTALL_DIR)/lib
# filter detail:
# - -s_*/.* : exclude all hidden files from being sent wherever they are
	$(RSYNC) \
	    --filter "-s_*/.*" \
	    $(LIB_FROM)/init $(BUILD_DIR)/$(CSTBOX_INSTALL_DIR)/lib

copy_init_scripts:
	@echo '------ copying init scripts...'
	mkdir -p \
	    $(BUILD_DIR)/$(INIT_D_INSTALL_DIR) 
	$(RSYNC) \
	    --filter "-s_*/.*" \
	    $(INIT_D_FROM)/cstbox* $(BUILD_DIR)/$(INIT_D_INSTALL_DIR)

copy_etc_files:
	@echo '------ copying etc files...'
	mkdir -p \
	    $(BUILD_DIR)/$(ETC_CSTBOX_INSTALL_DIR)
	$(RSYNC) \
	    --filter "-s_*/.*" \
	    $(ETC_FROM)/cstbox/ $(BUILD_DIR)/$(ETC_CSTBOX_INSTALL_DIR)

check_metadata_files:
	@echo '----- checking metadata files...'
	@for f in $$(find lib/python/pycstbox/devcfg.d/ -type f) ; do echo $$f ; cat $$f | python -mjson.tool > /dev/null || exit 1 ; done

upload: $(DEBPKG_NAME).deb
	@if [ -z "$(CBX_DEPLOY_PATH)" ] ; then \
		echo "*** CBX_DEPLOY_PATH must be set to the path where packages must be deployed" ;\
		exit 1 ;\
	fi
	@echo "----- uploading $(DEBPKG_NAME).deb to $(CBX_DEPLOY_PATH)"
	rsync -av $(DEBPKG_NAME).deb $(CBX_DEPLOY_PATH)$(DEBPKG_NAME).deb 

deploy: upload

clean:
	@echo '------ cleaning all...'
	\rm -f $(DEBPKG_NAME).deb 
	\rm -rf $(BUILD_DIR) 

.PHONY: i18n dist deploy css clean
