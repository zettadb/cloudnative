#! /bin/bash
# Copyright (c) 2019 ZettaDB inc. All rights reserved.
# This source code is licensed under Apache 2.0 License,
# combined with Common Clause Condition 1.0, as detailed in the NOTICE file.

script_dir="`dirname $0`"
. $script_dir/common.sh

mkdir -p temp
script="tmprun_$$.sh"
localscript="temp/$script"
remotescript="/tmp/$script"

hostitem="$1"
shift
cmd="$@"

ufail=0
ffail=0

host="${hostitem%:*}"
hname="${hostitem#*:}"

echo "=========== [`date`] execute ($cmd) on $host($hname) ==========="

echo "$cmd" > $localscript
sed -i "s#HOST_IP_ADDR#$host#g" $localscript
sed -i "s#HOST_NAME#$hname#g" "$localscript"

if test "$SSHPASS" = ""; then
	scp -P $sshport -o ConnectTimeout=$contimeout $localscript $REMOTE_USER@$host:/tmp || ufail=1
	if $tty; then
		ssh -p $sshport -o ConnectTimeout=$contimeout -t $REMOTE_USER@$host "bash $remotescript" || ufail=1
	else
		ssh -p $sshport -o ConnectTimeout=$contimeout $REMOTE_USER@$host "bash $remotescript" < /dev/null || ufail=1
	fi
	test "$clear" = "true" && ssh -p $sshport -o ConnectTimeout=$contimeout $REMOTE_USER@$host "rm -f $remotescript"
else
	sshpass -p "$REMOTE_PASSWORD" scp  -P $sshport -o ConnectTimeout=$contimeout $localscript $REMOTE_USER@$host:/tmp || ufail=1
	if $tty; then
		sshpass -p "$REMOTE_PASSWORD" ssh -p $sshport -o ConnectTimeout=$contimeout -t $REMOTE_USER@$host "bash $remotescript" || ufail=1
	else
		sshpass -p "$REMOTE_PASSWORD" ssh -p $sshport -o ConnectTimeout=$contimeout $REMOTE_USER@$host "bash $remotescript" < /dev/null || ufail=1
	fi
	test "$clear" = "true" && sshpass -p "$REMOTE_PASSWORD" ssh -p $sshport -o ConnectTimeout=$contimeout $REMOTE_USER@$host "rm -f $remotescript"
fi

if test "$ufail" = "1"; then
	ffail=1
	if test "$echofail" = "true"; then
		echo "!!!FAILURES!!!"
	fi
fi

rm -f $localscript
exit $ffail
