#!/bin/python2
# Copyright (c) 2019 ZettaDB inc. All rights reserved.
# This source code is licensed under Apache 2.0 License,
# combined with Common Clause Condition 1.0, as detailed in the NOTICE file.

import sys
import json
import getpass
import re
import time
import uuid
import os
import os.path
import argparse

def addIpToMachineMap(map, ip, args):
    if not map.has_key(ip):
	mac={"ip":ip, "user":args.defuser, "basedir":args.defbase}
	map[ip] = mac

def addMachineToMap(map, ip, user, basedir):
    mac={"ip":ip, "user":user, "basedir":basedir}
    map[ip] = mac

def addIpToFilesMap(map, ip, fname, targetdir):
    if not map.has_key(ip):
	map[ip] = {}
    tmap = map[ip]
    if not tmap.has_key(fname):
	tmap[fname] = targetdir

def addNodeToFilesMap(map, node, fname, targetdir):
    ip = node['ip']
    addIpToFilesMap(map, ip, fname, targetdir)

def addNodeToIpset(set, node):
    ip = node['ip']
    set.add(ip)

# Not used currently.
def addToCommandsMap(map, ip, targetdir, command):
    if not map.has_key(ip):
	map[ip] = []
    cmds = map[ip]
    cmds.append([targetdir, command])

def addToCommandsList(cmds, ip, targetdir, command, envtype="no"):
    lst = [ip, targetdir, command, envtype]
    cmds.append(lst)

def addToDirMap(map, ip, newdir):
    if not map.has_key(ip):
	map[ip] = []
    dirs = map[ip]
    dirs.append(newdir)

def getuuid():
    return str(uuid.uuid1())

def addPortToMachine(map, ip, port):
    if not map.has_key(ip):
	map[ip] = set([port])
    else:
        pset = map[ip]
        if port in pset:
            raise ValueError("duplicate port:%s on host:%s" % (str(port), ip))
        else:
            pset.add(port)

def addDirToMachine(map, ip, directory):
    if not map.has_key(ip):
	map[ip] = set([directory])
    else:
        dset = map[ip]
        if directory in dset:
            raise ValueError("duplicate directory:%s on host:%s" % (directory, ip))
        else:
            dset.add(directory)

def validate_config(jscfg):
    cluster = jscfg['cluster']
    meta = cluster['meta']
    comps = cluster['comp']['nodes']
    datas = cluster['data']
    portmap = {}
    dirmap = {}
    metacnt = len(meta['nodes'])
    if metacnt == 0:
        raise ValueError('Error: There must be at least one node in meta shard')

    hasPrimary=False
    for node in meta['nodes']:
        addPortToMachine(portmap, node['ip'], node['port'])
        addPortToMachine(portmap, node['ip'], node['xport'])
        addPortToMachine(portmap, node['ip'], node['mgr_port'])
        addDirToMachine(dirmap, node['ip'], node['data_dir_path'])
        addDirToMachine(dirmap, node['ip'], node['log_dir_path'])
        if node.has_key('innodb_log_dir_path'):
            addDirToMachine(dirmap, node['ip'], node['innodb_log_dir_path'])
        if node.get('is_primary', False):
            if hasPrimary:
                raise ValueError('Error: Two primaries found in meta shard, there should be one and only one Primary specified !')
            else:
                hasPrimary = True
    if metacnt > 1:
        if not hasPrimary:
            raise ValueError('Error: No primary found in meta shard, there should be one and only one primary specified !')
    else:
        node['is_primary'] = True

    for node in comps:
        addPortToMachine(portmap, node['ip'], node['port'])
        addDirToMachine(dirmap, node['ip'], node['datadir'])
    i=1
    for shard in datas:
        nodecnt = len(shard['nodes'])
        if nodecnt == 0:
            raise ValueError('Error: There must be at least one node in data shard%d' % i)
        if nodecnt > 1 and metacnt == 1:
            raise ValueError('Error: Meta shard has only one node, but data shard%d has two or more' % i)
        elif nodecnt == 1 and metacnt > 1:
            raise ValueError('Error: Meta shard has two or more node, but data shard%d has only one' % i)
        hasPrimary=False
        for node in shard['nodes']:
            addPortToMachine(portmap, node['ip'], node['port'])
            addPortToMachine(portmap, node['ip'], node['xport'])
            addPortToMachine(portmap, node['ip'], node['mgr_port'])
            addDirToMachine(dirmap, node['ip'], node['data_dir_path'])
            addDirToMachine(dirmap, node['ip'], node['log_dir_path'])
            if node.has_key('innodb_log_dir_path'):
                addDirToMachine(dirmap, node['ip'], node['innodb_log_dir_path'])
            if node.get('is_primary', False):
                if hasPrimary:
                    raise ValueError('Error: Two primaries found in shard%d, there should be one and only one Primary specified !' % i)
                else:
                    hasPrimary = True
        if metacnt > 1:
            if not hasPrimary:
                raise ValueError('Error: No primary found in shard%d, there should be one and only one primary specified !' % i)
        else:
            node['is_primary'] = True
        i+=1

def generate_haproxy_config(jscfg, machines, confname):
    cluster = jscfg['cluster']
    comps = cluster['comp']['nodes']
    haproxy = cluster['haproxy']
    mach = machines[haproxy['ip']]
    maxconn = haproxy.get('maxconn', 10000)
    conf = open(confname, 'w')
    conf.write('''# generated automatically
    global
        pidfile %s/haproxy.pid
        maxconn %d
        daemon
 
    defaults
        log global
        retries 5
        timeout connect 5s
        timeout client 30000s
        timeout server 30000s

    listen kunlun-cluster
        bind :%d
        mode tcp
        balance roundrobin
''' % (mach['basedir'], maxconn, haproxy['port']))
    i = 1
    for node in comps:
        conf.write("        server comp%d %s:%d weight 1 check inter 10s\n" % (i, node['ip'], node['port']))
        i += 1
    conf.close()

def generate_install_scripts(jscfg, args):
    validate_config(jscfg)

    installtype = args.installtype
    sudopfx=""
    if args.sudo:
        sudopfx="sudo "
    localip = '127.0.0.1'

    machines = {}
    for mach in jscfg['machines']:
	ip=mach['ip']
	user=mach.get('user', args.defuser)
	base=mach.get('basedir', args.defbase)
	addMachineToMap(machines, ip, user, base)

    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version

    filesmap = {}
    commandslist = []
    dirmap = {}
    usemgr=True

    cluster = jscfg['cluster']
    cluster_name = cluster['name']
    meta = cluster['meta']

    usemgr=False
    metacnt = len(meta['nodes'])
    if metacnt > 1:
        usemgr = True

    if not meta.has_key('group_uuid'):
	    meta['group_uuid'] = getuuid()
    my_metaname = 'mysql_meta.json'
    metaf = open(r'install/%s' % my_metaname,'w')
    json.dump(meta, metaf, indent=4)
    metaf.close()

    cmdpat = '%spython2 install-mysql.py --config=./%s --target_node_index=%d --cluster_id=%s --shard_id=%s'
    # commands like:
    # python2 install-mysql.py --config=./mysql_meta.json --target_node_index=0
    targetdir='%s/dba_tools' % storagedir
    i=0
    pries = []
    secs = []
    shard_id = "meta"
    for node in meta['nodes']:
	addNodeToFilesMap(filesmap, node, my_metaname, targetdir)
	addIpToMachineMap(machines, node['ip'], args)
	cmd = cmdpat % (sudopfx, my_metaname, i, cluster_name, shard_id)
	if node.get('is_primary', False):
		pries.append([node['ip'], targetdir, cmd])
	else:
		secs.append([node['ip'], targetdir, cmd])
	addToDirMap(dirmap, node['ip'], node['data_dir_path'])
	addToDirMap(dirmap, node['ip'], node['log_dir_path'])
        if node.has_key('innodb_log_dir_path'):
            addToDirMap(dirmap, node['ip'], node['innodb_log_dir_path'])
	i+=1

    datas = cluster['data']
    i=1
    for shard in datas:
	    if not shard.has_key('group_uuid'):
		    shard['group_uuid'] = getuuid()
            shard_id = "shard%d" % i
	    my_shardname = "mysql_shard%d.json" % i
	    shardf = open(r'install/%s' % my_shardname, 'w')
	    json.dump(shard, shardf, indent=4)
	    shardf.close()
	    j = 0
	    for node in shard['nodes']:
		addNodeToFilesMap(filesmap, node, my_shardname, targetdir)
		addIpToMachineMap(machines, node['ip'], args)
		cmd = cmdpat % (sudopfx, my_shardname, j, cluster_name, shard_id)
		if node.get('is_primary', False):
			pries.append([node['ip'], targetdir, cmd])
		else:
			secs.append([node['ip'], targetdir, cmd])
		addToDirMap(dirmap, node['ip'], node['data_dir_path'])
		addToDirMap(dirmap, node['ip'], node['log_dir_path'])
		if node.has_key('innodb_log_dir_path'):
		    addToDirMap(dirmap, node['ip'], node['innodb_log_dir_path'])
		j += 1
	    i+=1
    extraopt = " "
    if not usemgr:
        extraopt = " --ha_mode=no_rep"
    for item in pries:
        addToCommandsList(commandslist, item[0], item[1], item[2] + extraopt)
    for item in secs:
        addToCommandsList(commandslist, item[0], item[1], item[2] + extraopt)
    # This only needs to transfered to machine creating the cluster.
    pg_metaname = 'postgres_meta.json'
    metaf = open(r'install/%s' % pg_metaname, 'w')
    objs = []
    for node in meta['nodes']:
	obj = {}
	obj['ip'] = node['ip']
	obj['port'] = node['port']
	obj['user'] = "pgx"
	obj['password'] = "pgx_pwd"
	objs.append(obj)
    json.dump(objs, metaf, indent=4)
    metaf.close()

    # This only needs to transfered to machine creating the cluster.
    pg_shardname = 'postgres_shards.json'
    shardf = open(r'install/%s' % pg_shardname, 'w')
    shards = []
    i=1
    for shard in datas:
	obj={'shard_name': "shard%d" % i}
	i+=1
	nodes=[]
	for node in shard['nodes']:
	    n={'user':'pgx', 'password':'pgx_pwd'}
	    n['ip'] = node['ip']
	    n['port'] = node['port']
	    nodes.append(n)
	obj['shard_nodes'] = nodes
	shards.append(obj)
    json.dump(shards, shardf, indent=4)
    shardf.close()

    comps = cluster['comp']['nodes']
    pg_compname = 'postgres_comp.json'
    compf = open(r'install/%s' % pg_compname, 'w')
    json.dump(comps, compf, indent=4)
    compf.close()

    # python2 install_pg.py --config=docker-comp.json --install_ids=1,2,3
    targetdir="%s/scripts" % serverdir
    for node in comps:
	addNodeToFilesMap(filesmap, node, pg_compname, targetdir)
	addIpToMachineMap(machines, node['ip'], args)
	cmdpat = r'python2 install_pg.py  --config=./%s --install_ids=%d'
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (pg_compname, node['id']))
	addToDirMap(dirmap, node['ip'], node['datadir'])
    comp1 = comps[0]
    addNodeToFilesMap(filesmap, comp1, pg_metaname, targetdir)
    addNodeToFilesMap(filesmap, comp1, pg_shardname, targetdir)
    resourcedir = "%s/resources" % serverdir
    cmdpat=r'/bin/bash build_driver.sh'
    addToCommandsList(commandslist, comp1['ip'], resourcedir, cmdpat, "all")
    cmdpat=r'python2 bootstrap.py --config=./%s --bootstrap_sql=./meta_inuse.sql'
    addToCommandsList(commandslist, comp1['ip'], targetdir, cmdpat % pg_metaname, "storage")
    cmdpat='python2 create_cluster.py --shards_config=./%s \
--comps_config=./%s  --meta_config=./%s --cluster_name=%s --cluster_owner=abc --cluster_biz=test'
    if not usemgr:
        cmdpat = cmdpat + " --ha_mode=no_rep"
    addToCommandsList(commandslist, comp1['ip'], targetdir,
        cmdpat % (pg_shardname, pg_compname, pg_metaname, cluster_name), "all")

    # bash -x bin/cluster_mgr_safe --debug --pidfile=run.pid clustermgr.cnf >& run.log </dev/null &
    mgr_name = 'clustermgr.cnf'
    os.system('mkdir -p install')
    mgrf = open(r'install/%s' % mgr_name, 'w')
    mgrtempf = open(r'clustermgr.cnf.template','r')
    firstmeta = meta['nodes'][0]
    for line in mgrtempf:
	newline = re.sub('META_HOST', firstmeta['ip'], line)
	newline = re.sub('META_PORT', str(firstmeta['port']), newline)
	mgrf.write(newline)
    mgrtempf.close()
    mgrf.close()
    targetdir=clustermgrdir
    addIpToMachineMap(machines, cluster['clustermgr']['ip'], args)
    addIpToFilesMap(filesmap, cluster['clustermgr']['ip'], mgr_name, targetdir)
    cmdpat = r'bash -x bin/cluster_mgr_safe --debug --pidfile=run.pid %s >& run.log </dev/null &'
    addToCommandsList(commandslist, cluster['clustermgr']['ip'], targetdir, cmdpat % mgr_name, "clustermgr")

    haproxy = cluster.get("haproxy", None)
    if haproxy is not None:
        addIpToMachineMap(machines, haproxy['ip'], args)
        generate_haproxy_config(jscfg, machines, 'install/haproxy.cfg')
        cmdpat = r'haproxy-2.5.0-bin/sbin/haproxy -f haproxy.cfg >& haproxy.log'
        addToCommandsList(commandslist, haproxy['ip'], machines[haproxy['ip']]['basedir'], cmdpat)

    com_name = 'commands.sh'
    comf = open(r'install/%s' % com_name, 'w')
    comf.write('#! /bin/bash\n')

    # files copy.
    for ip in machines:
	mach = machines.get(ip)
	if args.sudo:
	    mkstr = "bash remote_run.sh --user=%s %s 'sudo mkdir -p %s && sudo chown -R %s:`id -gn %s` %s'\n"
	    tup= (mach['user'], ip, mach['basedir'], mach['user'], mach['user'], mach['basedir'])
	else:
	    mkstr = "bash remote_run.sh --user=%s %s 'mkdir -p %s'\n"
	    tup= (mach['user'], ip, mach['basedir'])
	comf.write(mkstr % tup)
	# Set up the files
	if installtype == 'full':
	    comstr = "bash dist.sh --hosts=%s --user=%s %s %s\n"
	    comf.write(comstr % (ip, mach['user'], '%s.tgz' % storagedir, mach['basedir']))
	    comf.write(comstr % (ip, mach['user'], '%s.tgz' % serverdir, mach['basedir']))
	    comf.write(comstr % (ip, mach['user'], '%s.tgz' % clustermgrdir, mach['basedir']))
            if cluster.has_key('haproxy'):
                comf.write(comstr % (ip, mach['user'], 'haproxy-2.5.0-bin.tar.gz', mach['basedir']))
	    extstr = "bash remote_run.sh --user=%s %s 'cd %s && tar -xzf %s'\n"
	    comf.write(extstr % (mach['user'], ip, mach['basedir'], '%s.tgz' % storagedir))
	    comf.write(extstr % (mach['user'], ip, mach['basedir'], '%s.tgz' % serverdir))
	    comf.write(extstr % (mach['user'], ip, mach['basedir'], '%s.tgz' % clustermgrdir))
            if cluster.has_key('haproxy'):
                comf.write(extstr % (mach['user'], ip, mach['basedir'], 'haproxy-2.5.0-bin.tar.gz'))

	# files
	fmap = {'build_driver.sh': '%s/resources' % serverdir, 'process_deps.sh': '.'}
        if cluster.has_key('haproxy'):
            fmap['haproxy.cfg'] = '.'
	for fname in fmap:
	    comstr = "bash dist.sh --hosts=%s --user=%s install/%s %s/%s\n"
	    tup=(ip, mach['user'], fname, mach['basedir'], fmap[fname])
	    comf.write(comstr % tup)

	comstr = "bash remote_run.sh --user=%s %s 'cd %s/%s || exit 1; test -d etc && echo > etc/instances_list.txt 2>/dev/null; exit 0'\n"
	comf.write(comstr % (mach['user'], ip, mach['basedir'], serverdir))
	comstr = "bash remote_run.sh --user=%s %s 'cd %s/%s || exit 1; test -d etc && echo > etc/instances_list.txt 2>/dev/null; exit 0'\n"
	comf.write(comstr % (mach['user'], ip, mach['basedir'], storagedir))

	# Set up the env.sh
	comstr = "bash dist.sh --hosts=%s --user=%s env.sh.template %s\n"
	extstr = ''' bash remote_run.sh --user=%s %s "cd %s && sed -s 's#KUNLUN_BASEDIR#%s#g' env.sh.template > env.sh" '''
	tup=(ip, mach['user'], mach['basedir'])
	exttup=(mach['user'], ip, mach['basedir'], mach['basedir'])
	comf.write(comstr % tup)
	comf.write(extstr % exttup)
	comf.write("\n")
        extstr = ''' bash remote_run.sh --user=%s %s "cd %s && sed -i 's#KUNLUN_VERSION#%s#g' env.sh" '''
        exttup=(mach['user'], ip, mach['basedir'], args.product_version)
	comf.write(extstr % exttup)
	comf.write("\n")

	comstr = "bash remote_run.sh --user=%s %s 'cd %s && envtype=storage && source ./env.sh && cd %s/lib && bash ../../process_deps.sh'\n"
	comf.write(comstr % (mach['user'], ip, mach['basedir'], storagedir))
	comstr = "bash remote_run.sh --user=%s %s 'cd %s && envtype=computing && source ./env.sh && cd %s/lib && bash ../../process_deps.sh'\n"
	comf.write(comstr % (mach['user'], ip, mach['basedir'], serverdir))
	comstr = "bash remote_run.sh --user=%s %s 'cd %s && envtype=clustermgr && source ./env.sh && cd %s/lib && bash ../../process_deps.sh'\n"
	comf.write(comstr % (mach['user'], ip, mach['basedir'], clustermgrdir))

    # dir making
    for ip in dirmap:
	mach = machines.get(ip)
	dirs=dirmap[ip]
	for d in dirs:
            if args.sudo:
	        mkstr = "bash remote_run.sh --user=%s %s 'sudo mkdir -p %s && sudo chown -R %s:`id -gn %s` %s'\n"
	        tup= (mach['user'], ip, d, mach['user'], mach['user'], d)
            else:
	        mkstr = "bash remote_run.sh --user=%s %s 'mkdir -p %s'\n"
	        tup= (mach['user'], ip, d)
	    comf.write(mkstr % tup)

    # files copy.
    for ip in filesmap:
	mach = machines.get(ip)
	# files
	fmap = filesmap[ip]
	for fname in fmap:
	    comstr = "bash dist.sh --hosts=%s --user=%s install/%s %s/%s\n"
	    tup=(ip, mach['user'], fname, mach['basedir'], fmap[fname])
	    comf.write(comstr % tup)

    # The reason for not using commands map is that,
    # we need to keep the order for the commands.
    for cmd in commandslist:
	ip=cmd[0]
	mach = machines[ip]
	mkstr = "bash remote_run.sh --user=%s %s $'cd %s && envtype=%s && source ./env.sh && cd %s || exit 1; %s'\n"
	tup= (mach['user'], ip, mach['basedir'], cmd[3], cmd[1], cmd[2])
	comf.write(mkstr % tup)

    comf.close()

# The order is meta shard -> data shards -> cluster_mgr -> comp nodes
def generate_start_scripts(jscfg, args):
    sudopfx=""
    if args.sudo:
        sudopfx="sudo "
    localip = '127.0.0.1'

    machines = {}
    for mach in jscfg['machines']:
	ip=mach['ip']
	user=mach.get('user', args.defuser)
	base=mach.get('basedir', args.defbase)
	addMachineToMap(machines, ip, user, base)

    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version

    filesmap = {}
    commandslist = []
    
    cluster = jscfg['cluster']
    meta = cluster['meta']
    # commands like:
    # bash startmysql.sh [port]
    targetdir='%s/dba_tools' % storagedir
    for node in meta['nodes']:
	addIpToMachineMap(machines, node['ip'], args)
	cmdpat = r'%sbash startmysql.sh %s'
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (sudopfx, node['port']))

    # bash startmysql.sh [port]
    targetdir='%s/dba_tools' % storagedir
    datas = cluster['data']
    for shard in datas:
	    for node in shard['nodes']:
		addIpToMachineMap(machines, node['ip'], args)
		cmdpat = r'%sbash startmysql.sh %s'
		addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (sudopfx, node['port']))
    
    # bash -x bin/cluster_mgr_safe --debug --pidfile=run.pid clustermgr.cnf >& run.log </dev/null &
    addIpToMachineMap(machines, cluster['clustermgr']['ip'], args)
    mgr_name = 'clustermgr.cnf'
    targetdir=clustermgrdir
    cmdpat = r'bash -x bin/cluster_mgr_safe --debug --pidfile=run.pid %s >& run.log </dev/null &'
    addToCommandsList(commandslist, cluster['clustermgr']['ip'], targetdir, cmdpat % mgr_name, "clustermgr")

    # su postgres -c "python2 start_pg.py port=5401"
    comps = cluster['comp']['nodes']
    targetdir="%s/scripts" % serverdir
    for node in comps:
	addIpToMachineMap(machines, node['ip'], args)
	cmdpat = r'python2 start_pg.py port=%d'
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'], "computing")

    haproxy = cluster.get("haproxy", None)
    if haproxy is not None:
        addIpToMachineMap(machines, haproxy['ip'], args)
        cmdpat = r'haproxy-2.5.0-bin/sbin/haproxy -f haproxy.cfg >& haproxy.log'
        addToCommandsList(commandslist, haproxy['ip'], machines[haproxy['ip']]['basedir'], cmdpat)

    com_name = 'commands.sh'
    os.system('mkdir -p start')
    comf = open(r'start/%s' % com_name, 'w')
    comf.write('#! /bin/bash\n')

    for cmd in commandslist:
	ip=cmd[0]
	mach = machines[ip]
	mkstr = "bash remote_run.sh --user=%s %s $'cd %s && envtype=%s && source ./env.sh && cd %s || exit 1; %s'\n"
	tup= (mach['user'], ip, mach['basedir'], cmd[3], cmd[1], cmd[2])
	comf.write(mkstr % tup)

    comf.close()

# The order is: comp-nodes -> cluster_mgr -> data shards -> meta shard
def generate_stop_scripts(jscfg, args):
    localip = '127.0.0.1'

    machines = {}
    for mach in jscfg['machines']:
	ip=mach['ip']
	user=mach.get('user', args.defuser)
	base=mach.get('basedir', args.defbase)
	addMachineToMap(machines, ip, user, base)

    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version

    commandslist = []
    cluster = jscfg['cluster']

    haproxy = cluster.get("haproxy", None)
    if haproxy is not None:
        addIpToMachineMap(machines, haproxy['ip'], args)
        cmdpat="cat haproxy.pid | xargs kill -9"
        addToCommandsList(commandslist, haproxy['ip'], machines[haproxy['ip']]['basedir'], cmdpat)

    # pg_ctl -D %s stop"
    comps = cluster['comp']['nodes']
    targetdir="%s/scripts" % serverdir
    for node in comps:
	addIpToMachineMap(machines, node['ip'], args)
	cmdpat = r'pg_ctl -D %s stop -m immediate'
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['datadir'], "computing")

    # bash -x bin/cluster_mgr_safe --debug --pidfile=run.pid --stop
    addIpToMachineMap(machines, cluster['clustermgr']['ip'], args)
    targetdir=clustermgrdir
    cmdpat = r"bash -x bin/cluster_mgr_safe --debug --pidfile=run.pid --stop"
    addToCommandsList(commandslist, cluster['clustermgr']['ip'], targetdir, cmdpat, "clustermgr")

    # bash stopmysql.sh [port]
    targetdir='%s/dba_tools' % storagedir
    datas = cluster['data']
    for shard in datas:
	    for node in shard['nodes']:
		addIpToMachineMap(machines, node['ip'], args)
		cmdpat = r'bash stopmysql.sh %d'
		addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'], "storage")

    meta = cluster['meta']
    # commands like:
    # mysqladmin --defaults-file=/kunlun/kunlun-storage-$version/etc/my_6001.cnf -uroot -proot shutdown
    targetdir='%s/dba_tools' % storagedir
    for node in meta['nodes']:
	addIpToMachineMap(machines, node['ip'], args)
	cmdpat = r'bash stopmysql.sh %d'
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'], "storage")
    
    com_name = 'commands.sh'
    os.system('mkdir -p stop')
    comf = open(r'stop/%s' % com_name, 'w')
    comf.write('#! /bin/bash\n')

    for cmd in commandslist:
	ip=cmd[0]
	mach = machines[ip]
	mkstr = "bash remote_run.sh --user=%s %s $'cd %s && envtype=%s && source ./env.sh && cd %s || exit 1; %s'\n"
	tup= (mach['user'], ip, mach['basedir'], cmd[3], cmd[1], cmd[2])
	comf.write(mkstr % tup)

    comf.close()

# The order is: comp-nodes -> cluster_mgr -> data shards -> meta shard
def generate_clean_scripts(jscfg, args):
    sudopfx=""
    if args.sudo:
        sudopfx="sudo "
    cleantype = args.cleantype
    localip = '127.0.0.1'

    machines = {}
    for mach in jscfg['machines']:
	ip=mach['ip']
	user=mach.get('user', args.defuser)
	base=mach.get('basedir', args.defbase)
	addMachineToMap(machines, ip, user, base)

    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version

    commandslist = []
    cluster = jscfg['cluster']

    haproxy = cluster.get("haproxy", None)
    if haproxy is not None:
        addIpToMachineMap(machines, haproxy['ip'], args)
        cmdpat="cat haproxy.pid | xargs kill -9"
        addToCommandsList(commandslist, haproxy['ip'], machines[haproxy['ip']]['basedir'], cmdpat)
        cmdpat="rm -f haproxy.pid"
        addToCommandsList(commandslist, haproxy['ip'], machines[haproxy['ip']]['basedir'], cmdpat)

    # pg_ctl -D %s stop"
    comps = cluster['comp']['nodes']
    targetdir="%s/scripts" % serverdir
    for node in comps:
	addIpToMachineMap(machines, node['ip'], args)
	cmdpat = r'pg_ctl -D %s stop -m immediate'
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['datadir'], "computing")
	cmdpat = r'%srm -fr %s'
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (sudopfx, node['datadir']))

    # bash -x bin/cluster_mgr_safe --debug --pidfile=run.pid --stop
    addIpToMachineMap(machines, cluster['clustermgr']['ip'], args)
    targetdir=clustermgrdir
    cmdpat = r"bash -x bin/cluster_mgr_safe --debug --pidfile=run.pid --stop"
    addToCommandsList(commandslist, cluster['clustermgr']['ip'], targetdir, cmdpat, "clustermgr")

    # bash stopmysql.sh [port]
    targetdir='%s/dba_tools' % storagedir
    datas = cluster['data']
    for shard in datas:
	    for node in shard['nodes']:
		addIpToMachineMap(machines, node['ip'], args)
		cmdpat = r'bash stopmysql.sh %d'
		addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'], "storage")
		cmdpat = r'%srm -fr %s'
		addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (sudopfx, node['log_dir_path']))
		addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (sudopfx, node['data_dir_path']))
		if node.has_key('innodb_log_dir_path'):
			addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (sudopfx, node['innodb_log_dir_path']))

    meta = cluster['meta']
    # commands like:
    # mysqladmin --defaults-file=/kunlun/kunlun-storage-$version/etc/my_6001.cnf -uroot -proot shutdown
    targetdir='%s/dba_tools' % storagedir
    for node in meta['nodes']:
	addIpToMachineMap(machines, node['ip'], args)
	cmdpat = r'bash stopmysql.sh %d'
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'], "storage")
	cmdpat = r'%srm -fr %s'
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (sudopfx, node['log_dir_path']))
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (sudopfx, node['data_dir_path']))
	if node.has_key('innodb_log_dir_path'):
		addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (sudopfx, node['innodb_log_dir_path']))

    if cleantype == 'full':
        for ip in machines:
            mach =machines[ip]
            cmdpat = '%srm -fr %s/*'
            addToCommandsList(commandslist, ip, "/", cmdpat % (sudopfx, mach['basedir']))

    com_name = 'commands.sh'
    os.system('mkdir -p clean')
    comf = open(r'clean/%s' % com_name, 'w')
    comf.write('#! /bin/bash\n')

    for cmd in commandslist:
	ip=cmd[0]
	mach = machines[ip]
	mkstr = "bash remote_run.sh --user=%s %s $'cd %s && envtype=%s && source ./env.sh && cd %s || exit 1; %s'\n"
	tup= (mach['user'], ip, mach['basedir'], cmd[3], cmd[1], cmd[2])
	comf.write(mkstr % tup)

    comf.close()

def checkdirs(dirs):
    for d in dirs:
	if not os.path.exists(d):
	    os.mkdir(d)

if  __name__ == '__main__':
    actions=["install", "start", "stop", "clean"]
    parser = argparse.ArgumentParser(description='Specify the arguments.')
    parser.add_argument('--action', type=str, help="The action", required=True, choices=actions)
    parser.add_argument('--config', type=str, help="The config path", required=True)
    parser.add_argument('--defuser', type=str, help="the command", default=getpass.getuser())
    parser.add_argument('--defbase', type=str, help="the command", default='/kunlun')
    parser.add_argument('--installtype', type=str, help="the install type", default='full', choices=['full', 'cluster'])
    parser.add_argument('--cleantype', type=str, help="the clean type", default='full', choices=['full', 'cluster'])
    parser.add_argument('--sudo', help="whether to use sudo", default=False, action='store_true')
    parser.add_argument('--product_version', type=str, help="kunlun version", default='0.9.1')

    args = parser.parse_args()
    checkdirs(actions)

    print str(sys.argv)
    jsconf = open(args.config)
    jstr = jsconf.read()
    jscfg = json.loads(jstr)
    jsconf.close()
    # print str(jscfg)

    if args.action == 'install':
	generate_install_scripts(jscfg, args)
    elif args.action == 'start':
	generate_start_scripts(jscfg, args)
    elif args.action == 'stop':
	generate_stop_scripts(jscfg, args)
    elif args.action == 'clean':
	generate_clean_scripts(jscfg, args)
    else :
	usage()
	sys.exit(1)
