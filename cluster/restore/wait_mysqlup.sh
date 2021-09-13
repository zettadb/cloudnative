#! /bin/bash

port="${1:-3306}"

while true; do
	mysql --defaults-file=$KUNLUNBASE/percona-8.0.18-bin-rel/etc/my_$port.cnf -uroot -proot -e 'select now()' >& /dev/null
	if test "$?" = "0"; then
		break;
	fi
	sleep 1
done
