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
# - CSTBox init.d scripts
INIT_D_FROM?=./init.d
# - CSTBox bin scripts
BIN_FROM?=./bin
# - CSTBox configuration files
ETC_FROM?=./res/etc

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
SUPPORT_PACKAGES_INSTALL_DIR=usr/lib/python$(PYTHON_VERSION)/dist-packages

# Computed locations

# - CSTBox Python package directory
CSTBOX_PACKAGES_INSTALL_DIR=$(CSTBOX_INSTALL_DIR)/lib/python/
# - CSTBox binaries directory
CSTBOX_BINARIES_INSTALL_DIR=$(CSTBOX_INSTALL_DIR)/bin

#RSYNC=rsync -av
RSYNC=rsync -Ca

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

# copy_files:
# CSTBox module Makefiles must define the copy_files rule and specify what 
# must be copied by assembling pre-defined rules as dependencies. 
# If no action other than pre-defined ones is needed, the rule can left empty. 
# It some other copy or action is neede, just put them in the rule content.
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
	@echo '------ copying pyCSTBox Python libray files...'
	mkdir -p \
	    $(BUILD_DIR)/$(CSTBOX_PACKAGES_INSTALL_DIR) 
# filter detail:
# - -s_*/.* : exclude all hidden files from being sent wherever they are
# - -s_*/x2dtools : exclude X2D tools sub-dirs
# - -s_*/attic : exclude deprecated stuff (stored in 'attic' directories)
	$(RSYNC) \
	    --filter "-s_*/.*" \
	    --filter "-s_*/x2dtools" \
	    --filter "-s_*/attic" \
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
	    --include "devcfg.d/**/*" \
	    --include "devcfg.d/*" \
	    --include "MANIFEST" \
	    --exclude "*" \
	    $(LIB_FROM)/python/pycstbox $(BUILD_DIR)/$(CSTBOX_PACKAGES_INSTALL_DIR)

copy_python_support_pkgs:
	@echo '------ copying addition Python support packages...'
	mkdir -p \
	    $(BUILD_DIR)/$(SUPPORT_PACKAGES_INSTALL_DIR) 
	$(RSYNC) \
	    --filter "-s_*/.*" \
	    $(LIB_FROM)/python/dist-packages/ $(BUILD_DIR)/$(SUPPORT_PACKAGES_INSTALL_DIR)


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

upload: dist
	@if [ -z "$(CBX_REMOTE)" ] ; then \
		echo "*** CBX_REMOTE must be set to target CSTBox host name or IP" ;\
		exit 1 ;\
	fi
	@echo "----- uploading $(DEBPKG_NAME).deb to $(CBX_REMOTE)"
	scp $(DEBPKG_NAME).deb $(CBX_REMOTE): 

clean:
	@echo '------ cleaning all...'
	rm -f $(DEBPKG_NAME).deb 
	rm -rf $(BUILD_DIR) 

.PHONY: i18n dist css clean
