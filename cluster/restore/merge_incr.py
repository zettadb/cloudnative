#! /usr/bin/python

import os
import sys
import re

def addLogToMap(lmap, logf, dirf):
	numdir = long(dirf)
	if not lmap.has_key(logf) or numdir > lmap[logf]:
		lmap[logf] = numdir
	# if not lmap.has_key(logf):
	#	lmap[logf] = [numdir]
	# else:
	#	lmap[logf].append(numdir)

def merge_binlog(incrdir, binlogpref, targetd):
	subdirs = os.listdir(incrdir)
	logmap = {}
	for d in subdirs:
		if re.match(r'[0-9]+', d):
			logd = "%s/%s/logfiles" % (incrdir, d)
			logs = os.listdir(logd)
			for l in logs:
				addLogToMap(logmap, l, d)
	
	for f in logmap:
		print "%s %d" % (f, logmap[f])
		os.system("cp -f %s/%d/logfiles/%s %s" % (incrdir, logmap[f], f, targetd))

if __name__ == '__main__':
	incrdir=sys.argv[1]
	binlogpref=sys.argv[2]
	targetd=sys.argv[3]
	merge_binlog(incrdir, binlogpref, targetd)
