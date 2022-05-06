#! /bin/bash

if test "$#" != 3; then
	echo "Usage: change_config config_file_path param_name param_value"
fi

cfile="$1"
name="$2"
value="$3"

sed -i "/$name.*=/d" $cfile
echo "$name = $value" >> $cfile
