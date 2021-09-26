#! /bin/bash
# Copyright (c) 2019 ZettaDB inc. All rights reserved.
# This source code is licensed under Apache 2.0 License,
# combined with Common Clause Condition 1.0, as detailed in the NOTICE file.

host="$1"
port="$2"
tablepref="$3"
max="${4:-30}"

i=0
while test "$i" -lt $max; do
	psql postgres://abc:abc@$host:$port/postgres -c "create table $tablepref$i(id integer primary key, info text);"
	let i++
done
