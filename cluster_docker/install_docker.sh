#! /bin/bash
# Copyright (c) 2019 ZettaDB inc. All rights reserved.
# This source code is licensed under Apache 2.0 License,
# combined with Common Clause Condition 1.0, as detailed in the NOTICE file.

pyvererr() {
	echo "Python 2 is not found!"
	exit 1
}

pycmd=python2
which $pycmd >& /dev/null || pycmd=python
pyver=""
which $pycmd >& /dev/null && pyver=`python --version 2>&1 | cut -d " " -f 2 | cut -d . -f 1`
test "$pyver" = "2" || pyvererr

$pycmd generate_docker_scripts.py config=./install_docker.json $*
bash ./install.sh
