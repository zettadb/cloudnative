#! /bin/bash
# Copyright (c) 2019 ZettaDB inc. All rights reserved.
# This source code is licensed under Apache 2.0 License,
# combined with Common Clause Condition 1.0, as detailed in the NOTICE file.

user="`id -un`"
group="`id -gn`"
prefix="$1"
setenv="${2:-1}"

mkdir -p $prefix/lib/python2.7/site-packages/
mkdir -p $prefix/lib64/python2.7/site-packages/
if test "$setenv" = "1":
	export PATH="`pwd`/../bin:$PATH"
	export LD_LIBRARY_PATH="`pwd`/../lib:$LD_LIBRARY_PATH"
fi
# Here we are in the kunlun-server-$VERSION/resources, so we can set the PATH and LD_LIBRARY_PATH
python2 -c 'import mysql.connector' >/dev/null 2>/dev/null || (
	tar -xzf mysql-connector-python-2.1.3.tar.gz
	cd mysql-connector-python-2.1.3
	python2 setup.py build >/dev/null
	python2 setup.py install --prefix="$prefix" >/dev/null
) 

python2 -c 'import psycopg2' >/dev/null 2>/dev/null || (
	tar -xzf psycopg2-2.8.4.tar.gz
	cd psycopg2-2.8.4
	python2 setup.py build_ext >/dev/null
	python2 setup.py install --prefix="$prefix" >/dev/null
)
