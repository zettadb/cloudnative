#! /bin/bash

if test "$#" -lt 1; then
	echo "usage: bash clear_instance.sh port storage|server [basedir] [version]" >&2
	exit 1
fi

p="$1"
cleartype="$2"
basedir="${3:-`pwd`}"
version="${4:-1.2.1}"
#cd $basedir/kunlun-node-manager-$version/bin && \
#bash stop_node_mgr.sh

cd $basedir
test -f env.sh.nodemgr && . ./env.sh.nodemgr
cd -

# port for mysqld_exporter or postgres_exporter
if test "$cleartype" = "storage"; then
	pp=`expr $p + 1`
	cd $basedir/instance_binaries/storage/$p/kunlun-storage-$version/dba_tools 2>/dev/null || exit 1
	export PATH=`pwd`/../bin:$PATH
	export LD_LIBRARY_PATH=`pwd`/../lib:$LD_LIBRARY_PATH
	bash stopmysql.sh $p
	# stop mysqld_exporter
	ps -fe | grep mysqld_exporter | grep ":$pp" | awk '{print $2}' | while read f; do kill -9 $f; done
	mycnf=`cat ../etc/instances_list.txt | sed '/^$/d' | sed 's/.*==>//g'`
	test "$mycnf" = "" && exit 0
	datadir_path=`cat $mycnf| grep -v 'rootdatadir' | grep 'datadir.*=' | sed -e 's/datadir.*= *//'`
	logdir_path=`cat $mycnf| grep '#log dir is=' | sed  's/#log dir is=//'`
	waldir_path=`cat $mycnf| grep 'innodb_log_group_home_dir.*=' | sed -e 's/innodb_log_group_home_dir.*= *//' -e 's#/redolog$##'`
	#echo "$p-datadir: $datadir_path"
	#echo "$p-logdir: $logdir_path"
	#echo "$p-waldir: $waldir_path"
	test "$datadir_path" = "" && exit 1
	test "$logdir_path" = "" && exit 1
	test "$waldir_path" = "" && exit 1
	rm -fr $datadir_path/*
	rm -fr $datadir_path
	rm -fr $logdir_path/*
	rm -fr $logdir_path
	rm -fr $waldir_path/*
	rm -fr $waldir_path
	rm -fr $basedir/instance_binaries/storage/$p
elif test "$cleartype" = "server"; then
	pp=`expr $p + 2`
	cd $basedir/instance_binaries/computer/$p/kunlun-server-$version/scripts 2>/dev/null || exit 1
	export PATH=`pwd`/../bin:$PATH
	export LD_LIBRARY_PATH=`pwd`/../lib:$LD_LIBRARY_PATH
	datadir=`cat ../etc/instances_list.txt | sed '/^$/d' | sed 's/.*==>//g'`
	test "$datadir" = "" && exit 1
	pg_ctl -D $datadir stop -m immediate
	# stop postgres_exporter
	ps -fe | grep postgres_exporter | grep ":$pp" | awk '{print $2}' | while read f; do kill -9 $f; done
	#echo "$p-datadir"
	rm -fr $datadir
	rm -fr $basedir/instance_binaries/computer/$p
fi
