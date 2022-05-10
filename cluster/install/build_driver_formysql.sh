#! /bin/bash
# Copyright (c) 2019 ZettaDB inc. All rights reserved.
# This source code is licensed under Apache 2.0 License,
# combined with Common Clause Condition 1.0, as detailed in the NOTICE file.

user="`id -un`"
group="`id -gn`"

python2 -c 'import mysql.connector' >/dev/null 2>/dev/null || (
	tar -xzf mysql-connector-python-2.1.3.tar.gz
	cd mysql-connector-python-2.1.3
	python2 setup.py build >/dev/null
	sudo PATH="$PATH" python2 setup.py install >/dev/null
	cd ..
	sudo chown -R $user:$group mysql-connector-python-2.1.3
) 
