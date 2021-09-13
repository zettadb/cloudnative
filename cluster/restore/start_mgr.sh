#! /bin/bash

usage() {
	echo "start_mgr.sh port ismaster"
	exit 1
}

if test "$#" -lt 2; then 
	usage
fi

port="$1"
ismaster="$2"
test "$ismaster" = "true" || test "$ismaster" = "false" || usage

echo "port: $port"
echo "ismaster: $ismaster"

if test "$ismaster" = "true"; then
	mgrsql="RESET SLAVE; SET GLOBAL group_replication_bootstrap_group=ON; \
START GROUP_REPLICATION; SET GLOBAL group_replication_bootstrap_group=OFF;"
else
	mgrsql="RESET SLAVE; START GROUP_REPLICATION;"
fi

echo "start mgr sql: $mgrsql"

mysql --defaults-file=$KUNLUNBASE/percona-8.0.18-bin-rel/etc/my_$port.cnf -uroot -proot -e "$mgrsql"
