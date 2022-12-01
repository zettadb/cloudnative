#! /bin/bash
# Copyright (c) 2019 ZettaDB inc. All rights reserved.
# This source code is licensed under Apache 2.0 License,
# combined with Common Clause Condition 1.0, as detailed in the NOTICE file.

tries=10
loops=5
export LD_LIBRARY_PATH="`pwd`:$LD_LIBRARY_PATH"
tempfile="tmp_out_f"
loop=0
while test "$loop" -lt "$loops"; do
	find ../bin -type f | while read f; do
		cur=0
		while test "$cur" -lt "$tries"; do
			ldd $f 2>/dev/null | grep 'not found' >&/dev/null || break
			ldd $f 2>/dev/null | grep 'not found' |  sed "s#$f:##g" | sed 's#: # #g' | awk '{print $1}' | while read libf; do
               			cp deps/`basename $libf` .
        		done
			let cur++
		done
		while true; do
			$f --help > $tempfile 2>&1 
			grep "symbol lookup error" $tempfile >/dev/null 2>/dev/null || break
			libsopath=`cat $tempfile | sed 's/.*\(symbol lookup error:[^:]*\):.*/\1/g' | cut -d : -f 2 | sed 's/^ *//g' | sed 's/ *$//g'`
			soname="`basename $libsopath`"
			test ! -f "deps/$soname" && test -d private && mv -f private private.saved && break
			cp deps/`basename $libsopath` . || break
		done
	done
	let loop++
done
