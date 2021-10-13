#! /bin/bash

script_dir="`dirname $0`"
. $script_dir/common.sh

# Use \$host to represent hostip or hostname value.

from="$1"
to="$2"

ffail=0
for hostitem in $hosts; do
	ufail=0
        host="${hostitem%:*}"
        hname="${hostitem#*:}"

  echo "=== [`date`] on $host ===" 
  echo "=== fetch ($from) to $to ==="
	#echo "=========== [`date`] fetch ($from) on $host($hname) to $to  ==========="
        if `ping -c 2 $host >/dev/null 2>/dev/null`; then
                :
        else
                echo "Unable to connect $host($hname) !"
                continue
        fi

	if test "$SSHPASS" = ""; then
		eval scp -q -r $REMOTE_USER@$host:$from $to || ufail=1
	else
		eval sshpass -p "$REMOTE_PASSWORD" scp -r $REMOTE_USER@$host:$from $to  || ufail=1
	fi

  if test "$ufail" = "1"; then
  	ffail=1
    echo -e "=== \033[31m !!!FAILURES!!! on $host \033[0m ==="
    echo " "
  else
    echo -e "=== \033[32m !!!SUCCESS!!! on $host \033[0m ===" 
    echo " "
  fi

done

exit $ffail
