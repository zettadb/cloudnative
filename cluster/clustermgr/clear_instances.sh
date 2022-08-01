#! /bin/bash

basedir="${1:-`pwd`}"
version="${2:-1.0.1}"

#cd $basedir/kunlun-node-manager-$version/bin && \
#bash stop_node_mgr.sh

cd $basedir
test -f env.sh.nodemgr && . ./env.sh.nodemgr
cd -

# clear the kunlun-storage instances
cd $basedir/instance_binaries/storage 2>/dev/null && \
ls | while read p; do
(
	bash $basedir/clear_instance.sh "$p" "storage" "$basedir"  "$version"
)
done
cd -
rm -fr $basedir/instance_binaries/storage/*

# clear the kunlun-server instances.
cd $basedir/instance_binaries/computer 2>/dev/null && \
ls | while read p; do
(
	bash $basedir/clear_instance.sh "$p" "server" "$basedir" "$version"
)
done
cd -
rm -fr $basedir/instance_binaries/computer/*
