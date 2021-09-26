#! /bin/bash

KUNLUNBASE=${KUNLUNBASE:-/kunlun}
port="$1"
logdir="$2"
datadir="$3"
backupdir="$4"
gtid="$5"


# The script should put the latest backuped gtid into file 'gtid'
# the file is put into the $backupdir
# And it need to copied back during backup process.

# The script should return 0 when it successfully to do backup,
# otherwise, it should return 1 when failures or not the
# suitable machine for backup.

# When finishing, it should put all things into a file
# named backup.tar.gz
# it contains the following things.
# * 1 gtid
# * 2 backup datafiles or log files.
cd $backupdir
rm -f backup.tar.gz

defarg="--defaults-file=$datadir/$port/my_$port.cnf"

# command to get the executed gtids is:
isslave=`mysql $defarg -uroot -proot -D mysql -s -e 'select @@read_only' 2>/dev/null | tail -n -1`
if test "$isslave" = "1"; then
	echo "this mysql is slave!"
	exit 0
elif test "$isslave" = ""; then
	echo "error when getting the role!"
	exit 1
fi

if test "$gtid" =  "0"; then
	xtrabackup $defarg --no-server-version-check \
		--backup --target-dir=base --user=root --password=root
	# The latest binlog info is in 'xtrabackup_binlog_info'
	# binf=`cat base/xtrabackup_binlog_info | cut -f 1`
	# pos=`cat base/xtrabackup_binlog_info | cut -f 2`
	gtid=`cat base/xtrabackup_binlog_info | cut -f 3`
	echo "$gtid" > gtid
	rm -f backup.tar.gz
	cp -f $datadir/$port/my_$port.cnf my.cnf
	tar -czf backup.tar.gz base gtid my.cnf
	rm -fr base
else
	fullpath=`pwd`
	binlogidx=`mysql $defarg -uroot -proot -D mysql -e 'select @@log_bin_index' 2>/dev/null  | tail -n +2`
	mkdir -p logfiles
	(
		cd $logdir
		python2 /$KUNLUNBASE/backup/check_gtid.py $gtid $binlogidx | while read f; do
			echo "Copying $f .... "
			cp -f $f $fullpath/logfiles
		done
	)
	gtid=`mysql $defarg -uroot -proot -D mysql -e 'select @@global.gtid_executed' 2>/dev/null  | tail -n +2 | sed 's/\\\\n//g'`
	echo "$gtid" > gtid
	rm -f backup.tar.gz
	tar -czf backup.tar.gz logfiles gtid
	rm -fr logfiles
fi
