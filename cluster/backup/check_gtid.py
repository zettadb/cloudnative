#! /bin/python2
import sys
progname='mysqlbinlogchecker'
import subprocess

def check_proc(gtids, indexfile):
    global progname
    gtidmap={}
    for gtid in gtids:
        pairs = gtid.split(':')
        # gtidmap[pairs[0]] = pairs[1]
        mv=long(pairs[1].split(':')[-1].split('-')[-1])
        gtidmap[pairs[0]] = mv
    # print gtidmap
    idxf = open(indexfile, 'r')
    lines = idxf.readlines()
    copyfiles=[]
    lines.reverse()
    for fname in lines:
        filename=fname.splitlines()[0]
        preids=[]
        #print "======= filename:%s =============" % filename
        result=subprocess.check_output([progname, filename])
        over=True
        for idtmp in result.split('\n')[1:-1] :
            gtid=idtmp.strip('#, ')
            if gtid.find('empty') >= 0:
                break
            pairs = gtid.split(':')
            mv=long(pairs[1].split(':')[-1].split('-')[-1])
            if not gtidmap.has_key(pairs[0]):
                copyfiles.append(filename)
                over=False
                break
            elif mv > gtidmap[pairs[0]]:
                copyfiles.append(filename)
                over=False
                break
            elif mv < gtidmap[pairs[0]]:
                break
        if over:
            copyfiles.append(filename)
            break
    copyfiles.reverse()
    for name in copyfiles:
        print name

if __name__ == '__main__':
    global gtidmap
    gtids=sys.argv[1].split(',')
    indexfile=sys.argv[2]
    check_proc(gtids, indexfile)
