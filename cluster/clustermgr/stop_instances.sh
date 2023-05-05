#! /bin/bash

basedir="${1:-`pwd`}"
version="${2:-1.2.1}"

#cd $basedir/kunlun-node-manager-$version/bin && \
#bash stop_node_mgr.sh

cd $basedir
test -f env.sh.nodemgr && . ./env.sh.nodemgr
cd -

# clear the kunlun-storage instances
cd $basedir/instance_binaries/storage 2>/dev/null && \
ls | while read p; do
(
	cd $p/kunlun-storage-$version/dba_tools || exit 1
	export PATH=`pwd`/../bin:$PATH
	export LD_LIBRARY_PATH=`pwd`/../lib:$LD_LIBRARY_PATH
	bash stopmysql.sh $p
	# stop mysqld_exporter
	pp=`expr $p + 1`
	ps -fe | grep mysqld_exporter | grep ":$pp" | awk '{print $2}' | while read f; do kill -9 $f; done
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
	pg_ctl -D $datadir stop -m immediate
	# stop postgres_exporter
	pp=`expr $p + 2`
	ps -fe | grep postgres_exporter | grep ":$pp" | awk '{print $2}' | while read f; do kill -9 $f; done
)
done
