#! /bin/bash
# Copyright (c) 2019 ZettaDB inc. All rights reserved.
# This source code is licensed under Apache 2.0 License,
# combined with Common Clause Condition 1.0, as detailed in the NOTICE file.

user="`id -un`"
group="`id -gn`"
prefix="$1"
MYSQLDRIVER_FILE=${MYSQLDRIVER_FILE:-mysql-connector-python-2.1.3.tar.gz}
MYSQLDRIVER_DIR=${MYSQLDRIVER_DIR:-mysql-connector-python-2.1.3}

python2 -c 'import mysql.connector' >/dev/null 2>/dev/null || (
	tar -xzf $MYSQLDRIVER_FILE
	cd $MYSQLDRIVER_DIR
	python2 setup.py build >/dev/null
	python2 setup.py install --prefix="$prefix" >/dev/null
) 
