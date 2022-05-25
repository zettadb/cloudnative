#! /bin/bash

basedir="${1:-`pwd`}"
version="${2:-0.9.2}"

#cd $basedir/kunlun-node-manager-$version/bin && \
#bash stop_node_mgr.sh

# clear the kunlun-storage instances
cd $basedir/instance_binaries/storage 2>/dev/null && \
ls | while read p; do
(
	cd $p/kunlun-storage-$version/dba_tools || exit 1
	export PATH=`pwd`/../bin:$PATH
	export LD_LIBRARY_PATH=`pwd`/../lib:$LD_LIBRARY_PATH
	bash stopmysql.sh $p
	mycnf=`cat ../etc/instances_list.txt | sed '/^$/d' | sed 's/.*==>//g'`
	test "$mycnf" = "" && continue
	datadir_path=`dirname $mycnf`
	logdir_path=`cat $mycnf| grep '#log dir is=' | sed  's/#log dir is=//' | sed 's#/dblogs$##'`
	waldir_path=`cat $mycnf| grep 'innodb_log_group_home_dir.*=' | sed -e 's/innodb_log_group_home_dir.*= *//' -e 's#/arch$##'`
	#echo "$p-datadir: $datadir_path"
	#echo "$p-logdir: $logdir_path"
	#echo "$p-waldir: $waldir_path"
	test "$datadir_path" = "" && exit 1
	test "$logdir_path" = "" && exit 1
	test "$waldir_path" = "" && exit 1
	rm -fr $datadir_path/*
	rm -fr $logdir_path/*
	rm -fr $waldir_path/*
)
done

# clear the kunlun-server instances.
cd $basedir/instance_binaries/computer 2>/dev/null && \
ls | while read p; do
(
	cd $p/kunlun-server-$version/scripts || exit 1
	export PATH=`pwd`/../bin:$PATH
	export LD_LIBRARY_PATH=`pwd`/../lib:$LD_LIBRARY_PATH
	datadir=`cat ../etc/instances_list.txt | sed '/^$/d' | sed 's/.*==>//g'`
	test "$datadir" = "" && exit 1
	pg_ctl -D $datadir stop -m immedidate
	#echo "$p-datadir"
	rm -fr $datadir/*
)
done
