#! /bin/bash

port="${1:-5432}"
while true; do
	psql postgres://abc:abc@localhost:$port/postgres -c 'select now();' >& /dev/null
	if test "$?" = "0"; then
		break;
	fi
	sleep 1
done
