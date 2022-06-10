#! /bin/bash

brpcport="${1}"
basedir="${2:-`pwd`}"
version="${3:-0.9.2}"

#cd $basedir/kunlun-node-manager-$version/bin && \
#bash start_node_mgr.sh

cd $basedir
test -f env.sh.$brpcport && . ./env.sh.$brpcport
cd -

# clear the kunlun-storage instances
cd $basedir/instance_binaries/storage 2>/dev/null && \
ls | while read p; do
(
	cd $p/kunlun-storage-$version/dba_tools || exit 1
	export PATH=`pwd`/../bin:$PATH
	export LD_LIBRARY_PATH=`pwd`/../lib:$LD_LIBRARY_PATH
	bash startmysql.sh $p
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
	python2 start_pg.py --port=$p
)
done
