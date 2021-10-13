#! /bin/bash

port="${1:-3306}"

while true; do
	mysql --defaults-file=$2 -uroot -proot -e 'select now()' >& /dev/null
	if test "$?" = "0"; then
		break;
	fi
	sleep 1
done
