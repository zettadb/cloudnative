#! /bin/bash

pgurl="$1"
cat serial_schedule | grep -v '^#'  | awk '{print $2}' | while read f; do
psql -f $f.sql $pgurl
done
