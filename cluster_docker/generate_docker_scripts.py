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

def addToCommandsList(cmds, ip, targetdir, command):
    lst = [ip, targetdir, command]
    cmds.append(lst)

def addToDirMap(map, ip, newdir):
    if not map.has_key(ip):
	map[ip] = []
    dirs = map[ip]
    dirs.append(newdir)

def getuuid():
    return uuid.uuid1()

def generate_install_scripts(jscfg, args):
    localip = '127.0.0.1'

    machines = {}
    for mach in jscfg['machines']:
	ip=mach['ip']
	user=mach.get('user', args.defuser)
	base=mach.get('basedir', args.defbase)
	addMachineToMap(machines, ip, user, base)

    filesmap = {}
    commandslist = []
    storagedatadir="/storage/data"
    storagedataattr="data_dir_path"
    storagelogdir="/storage/log"
    storagelogattr="log_dir_path"
    storageinnodir="/storage/innolog"
    stoargeinnoattr="innodb_log_dir_path"
    compdatadir="/pgdatadir"
    compdataattr="datadir"

    cluster = jscfg['cluster']
    meta = cluster['meta']
    network = jscfg.get('network', 'klnet')
    defbufstr='1024M'

    # Meta nodes
    metanodes = []
    mgrlist=[]
    i=1
    for node in meta['nodes']:
	name="mgr%s" % i
	metaobj={"port":3306, "user":"pgx", "password":"pgx_pwd", "ip":name,
		"hostip":node['ip'], "is_primary":node.get('is_primary', False),
		"buf":node.get('innodb_buffer_pool_size', defbufstr), "orig":node}
	mgrlist.append(name+":33062")
	metanodes.append(metaobj)
	addIpToMachineMap(machines, node['ip'], args)
	i+=1
    seed=",".join(mgrlist)
    # docker run -itd --network klnet --name mgr1a -h mgr1a [-v path_host:path_container] kunlun_mysql /bin/bash start_mysql.sh \
    # 237d8a1c-39ec-11eb-92aa-7364f9a0e147 mgr1a:33062 mgr1a:33062,mgr1b:33062,mgr1c:33062 1 true 0 0
    cmdpat= "sudo docker run -itd --network %s --name %s -h %s %s kunlun_mysql /bin/bash start_mysql.sh %s %s %s %d %s 0 0 %s"
    waitcmdpat="sudo docker exec %s /bin/bash /kunlun/wait_mysqlup.sh"
    i=1
    uuid=getuuid()
    secmdlist=[]
    priwaitlist=[]
    sewaitlist=[]
    for node in metanodes:
	targetdir="."
	buf=node['buf']
	orig = node['orig']
	mountarg=""
	if orig.has_key(storagedataattr):
		mountarg = mountarg + " -v %s:%s" % (orig[storagedataattr], storagedatadir)
	if orig.has_key(storagelogattr):
		mountarg = mountarg + " -v %s:%s" % (orig[storagelogattr], storagelogdir)
	if orig.has_key(stoargeinnoattr):
		mountarg = mountarg + " -v %s:%s" % (orig[stoargeinnoattr], storageinnodir)
	if node['is_primary']:
	    addToCommandsList(commandslist, node['hostip'], targetdir,
		cmdpat % (network, node['ip'], node['ip'], mountarg, uuid,
		    node['ip']+":33062", seed, i, str(node['is_primary']).lower(), buf))
	    addToCommandsList(priwaitlist, node['hostip'], targetdir,	waitcmdpat % (node['ip']))
	else:
	    addToCommandsList(secmdlist, node['hostip'], targetdir,
		cmdpat % (network, node['ip'], node['ip'], mountarg, uuid,
		    node['ip']+":33062", seed, i, str(node['is_primary']).lower(), buf))
	    addToCommandsList(sewaitlist, node['hostip'], targetdir, waitcmdpat % (node['ip']))
	del node['hostip']
	del node['is_primary']
	del node['buf']
	del node['orig']
	i+=1
    pg_metaname = 'docker-meta.json'
    metaf = open(pg_metaname, 'w')
    json.dump(metanodes, metaf, indent=4)
    metaf.close()

    # Data nodes
    datas = cluster['data']
    datanodes = []
    i = 1
    for shard in datas:
	shardname="shard%s" % i
	nodes=[]
	nodelist=[]
	j=1
        for node in shard['nodes']:
	    bufsize=node.get('innodb_buffer_pool_size', "")
	    name="%s_%d" % (shardname, j)
	    nodeobj={"port":3306, "user":"pgx", "password":"pgx_pwd", "ip":name,
		"hostip":node['ip'], "is_primary":node.get('is_primary', False),
		"buf":node.get('innodb_buffer_pool_size', defbufstr), "orig":node}
	    nodelist.append(name+":33062")
	    nodes.append(nodeobj)
	    addIpToMachineMap(machines, node['ip'], args)
	    j += 1
	j=1
	seed=",".join(nodelist)
	uuid=getuuid()
	tmpcmdlist = []
	for node in nodes:
	    targetdir="."
	    buf=node['buf']
	    orig = node['orig']
	    mountarg=""
	    if orig.has_key(storagedataattr):
	        mountarg = mountarg + " -v %s:%s" % (orig[storagedataattr], storagedatadir)
	    if orig.has_key(storagelogattr):
	        mountarg = mountarg + " -v %s:%s" % (orig[storagelogattr], storagelogdir)
	    if orig.has_key(stoargeinnoattr):
	        mountarg = mountarg + " -v %s:%s" % (orig[stoargeinnoattr], storageinnodir)
	    if node['is_primary']:
		addToCommandsList(commandslist, node['hostip'], targetdir,
		    cmdpat % (network, node['ip'], node['ip'], mountarg, uuid,
			node['ip']+":33062", seed, i, str(node['is_primary']).lower(), buf))
		addToCommandsList(priwaitlist, node['hostip'], targetdir, waitcmdpat % (node['ip']))
	    else:
		addToCommandsList(secmdlist, node['hostip'], targetdir,
		    cmdpat % (network, node['ip'], node['ip'], mountarg, uuid,
			node['ip']+":33062", seed, i, str(node['is_primary']).lower(), buf))
		addToCommandsList(sewaitlist, node['hostip'], targetdir, waitcmdpat % (node['ip']))
	    del node['hostip']
	    del node['is_primary']
	    del node['buf']
	    del node['orig']
	    j+=1
	shard_obj={"shard_name":shardname, "shard_nodes":nodes}
	datanodes.append(shard_obj)
	i+=1
    pg_shardname = 'docker-shards.json'
    shardf = open(pg_shardname, 'w')
    json.dump(datanodes, shardf, indent=4)
    shardf.close()

    commandslist.extend(priwaitlist)
    commandslist.extend(secmdlist)
    commandslist.extend(sewaitlist)
    
    # Comp nodes
    comps = cluster['comp']['nodes']
    compnodes=[]
    # sudo docker run -itd --network klnet --name comp1 -h comp1 -p 6401:5432 [-v path_host:path_container] kunlun_postgres /bin/bash start_postgres.sh 1
    cmdpat=r'sudo docker run -itd --network %s --name %s -h %s -p %d:5432 %s kunlun_postgres /bin/bash start_postgres.sh %d %s "%s"'
    waitcmdpat="sudo docker exec %s /bin/bash /kunlun/wait_pgup.sh"
    waitlist=[]
    i=1
    comp1=None
    comp1ip = None
    isfirst=True
    for node in comps:
	targetdir="."
	localport=node['port']
	localip=node['ip']
	name="comp%d" % i
	comp={"id":i, "user":node['user'], "password":node['password'],
	    "name":name, "ip":name, "port":5432}
	compnodes.append(comp)
	mountarg=""
	if node.has_key(compdataattr):
	    mountarg = "-v %s:%s" % (node[compdataattr], compdatadir)
	addToCommandsList(commandslist, localip, targetdir,
	    cmdpat % (network, name, name, node['port'], mountarg, i, node['user'], node['password']))
	addToCommandsList(waitlist, localip, targetdir,  waitcmdpat % (name))
	addIpToMachineMap(machines, node['ip'], args)
	if isfirst:
	    isfirst = False
	    comp1 = comp
	    comp1ip = localip
	i+=1
    pg_compname = 'docker-comp.json'
    compf = open(pg_compname, 'w')
    json.dump(compnodes, compf, indent=4)
    compf.close()

    # Copy the config
    targetdir="."
    cmdpat="sudo docker cp %s %s:/kunlun"
    addToCommandsList(commandslist, comp1ip, targetdir, cmdpat % (pg_metaname, comp1['name']))
    addToCommandsList(commandslist, comp1ip, targetdir, cmdpat % (pg_shardname, comp1['name']))
    addToCommandsList(commandslist, comp1ip, targetdir, cmdpat % (pg_compname, comp1['name']))

    # Init the cluster
    cmdpat = "sudo docker exec %s /bin/bash /kunlun/init_cluster.sh"
    addToCommandsList(commandslist, comp1ip, targetdir, cmdpat % (comp1['name']))

    # clustermgr
    targetdir="."
    name="clustermgr"
    addIpToMachineMap(machines, cluster['clustermgr']['ip'], args)
    cmdpat="sudo docker run -itd --network %s --name %s -h %s kunlun_clustermgr /bin/bash /kunlun/start_clustermgr.sh %s"
    addToCommandsList(commandslist, cluster['clustermgr']['ip'], targetdir,
	    cmdpat % (network, name, name, metanodes[0]['ip']))

    com_name = 'install.sh'
    comf = open(com_name, 'w')
    comf.write('#! /bin/bash\n')
    comf.write('# this file is generated automatically, please do not edit it manually.\n')

    # dir making
    for ip in machines:
	mach = machines.get(ip)
	mkstr = "bash remote_run.sh --user=%s %s 'sudo mkdir -p %s && sudo chown -R %s:`id -gn %s` %s'\n"
	tup= (mach['user'], ip, mach['basedir'], mach['user'], mach['user'], mach['basedir'])
	comf.write(mkstr % tup)
	files=['kunlun_clustermgr.tar.gz', 'kunlun_mysql.tar.gz', 'kunlun_postgres.tar.gz']
	if ip == comp1ip:
	    files.extend([pg_metaname, pg_shardname, pg_compname])
	for f in files:
	    comstr = "bash dist.sh --hosts=%s --user=%s %s %s\n"
	    tup= (ip, mach['user'], f, mach['basedir'])
	    comf.write(comstr % tup)
	comstr = "bash remote_run.sh --user=%s %s 'cd %s || exit 1 ; sudo docker inspect %s >& /dev/null || \
( gzip -cd %s.tar.gz | sudo docker load )' \n"
	comf.write(comstr % (mach['user'], ip, mach['basedir'], 'kunlun_clustermgr', 'kunlun_clustermgr'))
	comf.write(comstr % (mach['user'], ip, mach['basedir'], 'kunlun_mysql', 'kunlun_mysql'))
	comf.write(comstr % (mach['user'], ip, mach['basedir'], 'kunlun_postgres', 'kunlun_postgres'))

    # The reason for not using commands map is that,
    # we need to keep the order for the commands.
    for cmd in commandslist:
	ip=cmd[0]
	mach = machines[ip]
	mkstr = "bash remote_run.sh --user=%s %s 'cd %s && cd %s || exit 1; %s'\n"
	tup= (mach['user'], ip, mach['basedir'], cmd[1], cmd[2])
	comf.write(mkstr % tup)

    comf.close()

def generate_start_scripts(jscfg, args):
    localip = '127.0.0.1'

    machines = {}
    for mach in jscfg['machines']:
	ip=mach['ip']
	user=mach.get('user', args.defuser)
	base=mach.get('basedir', args.defbase)
	addMachineToMap(machines, ip, user, base)

    commandslist = []
    waitlist = []

    cluster = jscfg['cluster']
    meta = cluster['meta']

    cmdpat= "sudo docker container start %s"
    waitcmdpat="sudo docker exec %s /bin/bash /kunlun/wait_mysqlup.sh"
    targetdir = "/"
    # Meta nodes
    i=1
    for node in meta['nodes']:
	name="mgr%s" % i
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % name)
	addToCommandsList(waitlist, node['ip'], targetdir, waitcmdpat % name)
	addIpToMachineMap(machines, node['ip'], args)
	i+=1

    # Data nodes
    datas = cluster['data']
    i = 1
    for shard in datas:
	shardname="shard%s" % i
	j=1
        for node in shard['nodes']:
	    name="%s_%d" % (shardname, j)
	    addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % name)
	    addToCommandsList(waitlist, node['ip'], targetdir, waitcmdpat % name)
	    addIpToMachineMap(machines, node['ip'], args)
	    j += 1
	i += 1
    commandslist.extend(waitlist)

    waitlist = []

    # clustermgr
    name="clustermgr"
    addIpToMachineMap(machines, cluster['clustermgr']['ip'], args)
    addToCommandsList(commandslist, cluster['clustermgr']['ip'], targetdir, cmdpat % name)

    # Comp nodes
    comps = cluster['comp']['nodes']
    waitcmdpat="sudo docker exec %s /bin/bash /kunlun/wait_pgup.sh"
    i=1
    for node in comps:
	localip=node['ip']
	name="comp%d" % i
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % name)
	addToCommandsList(waitlist, node['ip'], targetdir, waitcmdpat % name)
	i+=1
    commandslist.extend(waitlist)

    com_name = 'start.sh'
    comf = open(com_name, 'w')
    comf.write('#! /bin/bash\n')
    comf.write('# this file is generated automatically, please do not edit it manually.\n')

    # The reason for not using commands map is that,
    # we need to keep the order for the commands.
    for cmd in commandslist:
	ip=cmd[0]
	mach = machines[ip]
	mkstr = "bash remote_run.sh --user=%s %s 'cd %s && cd %s || exit 1; %s'\n"
	tup= (mach['user'], ip, mach['basedir'], cmd[1], cmd[2])
	comf.write(mkstr % tup)

    comf.close()

def generate_stop_scripts(jscfg, args):
    localip = '127.0.0.1'

    machines = {}
    for mach in jscfg['machines']:
	ip=mach['ip']
	user=mach.get('user', args.defuser)
	base=mach.get('basedir', args.defbase)
	addMachineToMap(machines, ip, user, base)

    commandslist = []
    cluster = jscfg['cluster']
    meta = cluster['meta']

    cmdpat= "sudo docker container stop %s"
    targetdir = "/"
    # Meta nodes
    i=1
    for node in meta['nodes']:
	name="mgr%s" % i
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % name)
	addIpToMachineMap(machines, node['ip'], args)
	i+=1

    # Data nodes
    datas = cluster['data']
    i = 1
    for shard in datas:
	shardname="shard%s" % i
	j=1
        for node in shard['nodes']:
	    name="%s_%d" % (shardname, j)
	    addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % name)
	    addIpToMachineMap(machines, node['ip'], args)
	    j += 1
	i += 1

    # clustermgr
    name="clustermgr"
    addIpToMachineMap(machines, cluster['clustermgr']['ip'], args)
    addToCommandsList(commandslist, cluster['clustermgr']['ip'], targetdir, cmdpat % name)

    # Comp nodes
    comps = cluster['comp']['nodes']
    i=1
    for node in comps:
	localip=node['ip']
	name="comp%d" % i
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % name)
	i+=1

    com_name = 'stop.sh'
    comf = open(com_name, 'w')
    comf.write('#! /bin/bash\n')
    comf.write('# this file is generated automatically, please do not edit it manually.\n')

    # The reason for not using commands map is that,
    # we need to keep the order for the commands.
    for cmd in commandslist:
	ip=cmd[0]
	mach = machines[ip]
	mkstr = "bash remote_run.sh --user=%s %s 'cd %s && cd %s || exit 1 ; %s'\n"
	tup= (mach['user'], ip, mach['basedir'], cmd[1], cmd[2])
	comf.write(mkstr % tup)

    comf.close()

def generate_clean_scripts(jscfg, args):
    localip = '127.0.0.1'
    storagedatadir="/storage/data"
    storagedataattr="data_dir_path"
    storagelogdir="/storage/log"
    storagelogattr="log_dir_path"
    storageinnodir="/storage/innolog"
    stoargeinnoattr="innodb_log_dir_path"
    compdatadir="/pgdatadir"
    compdataattr="datadir"

    machines = {}
    for mach in jscfg['machines']:
	ip=mach['ip']
	user=mach.get('user', args.defuser)
	base=mach.get('basedir', args.defbase)
	addMachineToMap(machines, ip, user, base)

    commandslist = []
    cluster = jscfg['cluster']
    meta = cluster['meta']

    cmdpat= "sudo docker container rm -f %s"
    rmcmdpat = "sudo rm -fr %s"
    targetdir = "/"
    # Meta nodes
    i=1
    for node in meta['nodes']:
	name="mgr%s" % i
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % name)
	if node.has_key(storagedataattr):
	    addToCommandsList(commandslist, node['ip'], targetdir, rmcmdpat % node[storagedataattr])
	if node.has_key(storagelogattr):
	    addToCommandsList(commandslist, node['ip'], targetdir, rmcmdpat % node[storagelogattr])
	if node.has_key(stoargeinnoattr):
	    addToCommandsList(commandslist, node['ip'], targetdir, rmcmdpat % node[stoargeinnoattr])
	addIpToMachineMap(machines, node['ip'], args)
	i+=1

    # Data nodes
    datas = cluster['data']
    i = 1
    for shard in datas:
	shardname="shard%s" % i
	j=1
        for node in shard['nodes']:
	    name="%s_%d" % (shardname, j)
	    addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % name)
	    if node.has_key(storagedataattr):
	        addToCommandsList(commandslist, node['ip'], targetdir, rmcmdpat % node[storagedataattr])
	    if node.has_key(storagelogattr):
	        addToCommandsList(commandslist, node['ip'], targetdir, rmcmdpat % node[storagelogattr])
	    if node.has_key(stoargeinnoattr):
	        addToCommandsList(commandslist, node['ip'], targetdir, rmcmdpat % node[stoargeinnoattr])
	    addIpToMachineMap(machines, node['ip'], args)
	    j += 1
	i += 1

    # clustermgr
    name="clustermgr"
    addIpToMachineMap(machines, cluster['clustermgr']['ip'], args)
    addToCommandsList(commandslist, cluster['clustermgr']['ip'], targetdir, cmdpat % name)

    # Comp nodes
    comps = cluster['comp']['nodes']
    i=1
    for node in comps:
	localip=node['ip']
	name="comp%d" % i
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % name)
	if node.has_key(compdataattr):
	    addToCommandsList(commandslist, node['ip'], targetdir, rmcmdpat % node[compdataattr])
	i+=1

    for ip in machines:
	    mach =machines[ip]
	    cmdpat = 'sudo docker image rm -f %s'
	    addToCommandsList(commandslist, ip, "/", cmdpat % 'kunlun_mysql')
	    addToCommandsList(commandslist, ip, "/", cmdpat % 'kunlun_postgres')
	    addToCommandsList(commandslist, ip, "/", cmdpat % 'kunlun_clustermgr')
	    cmdpat = 'rm -f %s'
	    addToCommandsList(commandslist, ip, ".", cmdpat % 'kunlun_clustermgr.tar.gz')
	    addToCommandsList(commandslist, ip, ".", cmdpat % 'kunlun_mysql.tar.gz')
	    addToCommandsList(commandslist, ip, ".", cmdpat % 'kunlun_postgres.tar.gz')

    com_name = 'clean.sh'
    comf = open(com_name, 'w')
    comf.write('#! /bin/bash\n')
    comf.write('# this file is generated automatically, please do not edit it manually.\n')

    # The reason for not using commands map is that,
    # we need to keep the order for the commands.
    for cmd in commandslist:
	ip=cmd[0]
	mach = machines[ip]
	mkstr = "bash remote_run.sh --user=%s %s 'cd %s && cd %s || exit 1; %s'\n"
	tup= (mach['user'], ip, mach['basedir'], cmd[1], cmd[2])
	comf.write(mkstr % tup)

    comf.close()

if  __name__ == '__main__':
    actions=["install", "start", "stop", "clean"]
    parser = argparse.ArgumentParser(description='Specify the arguments.')
    parser.add_argument('--action', type=str, help="The action", required=True, choices=actions)
    parser.add_argument('--config', type=str, help="The config path", required=True)
    parser.add_argument('--defuser', type=str, help="the command", default=getpass.getuser())
    parser.add_argument('--defbase', type=str, help="the command", default='/kunlun')

    args = parser.parse_args()
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
