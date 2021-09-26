#! /bin/bash

KUNLUNBASE=${KUNLUNBASE:-/kunlun}

port="$1"
backupdir="$2"

# The script should do the back and save the files into $backupdir
# The logic is to be determined.

cd $backupdir
rm -f backup.tar.gz data.dump

pg_dump -Uabc -p$port -dpostgres > data.dump
tar -czf backup.tar.gz data.dump
