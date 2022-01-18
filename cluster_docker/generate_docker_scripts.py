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
    storagedataattr="data_dir_path"
    storagelogattr="log_dir_path"
    stoargeinnoattr="innodb_log_dir_path"
    compdataattr="datadir"

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
        if node.has_key(storagedataattr):
            addDirToMachine(dirmap, node['ip'], node[storagedataattr])
        if node.has_key(storagelogattr):
            addDirToMachine(dirmap, node['ip'], node[storagelogattr])
        if node.has_key(stoargeinnoattr):
            addDirToMachine(dirmap, node['ip'], node[stoargeinnoattr])
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
        if node.has_key(compdataattr):
            addDirToMachine(dirmap, node['ip'], node[compdataattr])
        addPortToMachine(portmap, node['ip'], node['port'])
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
            if node.has_key(storagedataattr):
                addDirToMachine(dirmap, node['ip'], node[storagedataattr])
            if node.has_key(storagelogattr):
                addDirToMachine(dirmap, node['ip'], node[storagelogattr])
            if node.has_key(stoargeinnoattr):
                addDirToMachine(dirmap, node['ip'], node[stoargeinnoattr])
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

    localip = "127.0.0.1"
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
    namespace = cluster.get('namespace', args.namespace)
    meta = cluster['meta']
    cluster_name = cluster.get('name', 'clust1')
    network = jscfg.get('network', 'klnet')
    defbufstr='1024MB'

    usemgr = False
    metacnt = len(meta['nodes'])
    if metacnt > 1:
        usemgr = True

    # Meta nodes
    metanodes = []
    metalist=[]
    i=1
    for node in meta['nodes']:
	name="%s.meta%s" % (namespace, i)
	metaobj={"port":3306, "user":"pgx", "password":"pgx_pwd", "ip":name,
		"hostip":node['ip'], "is_primary":node.get('is_primary', False),
		"buf":node.get('innodb_buffer_pool_size', defbufstr), "orig":node,
                "dockeropts": node.get('dockeropts', args.default_dockeropts)}
	metalist.append(name)
	metanodes.append(metaobj)
	addIpToMachineMap(machines, node['ip'], args)
	i+=1
    iplist=",".join(metalist)
    # docker run -itd --network klnet --name mgr1a -h mgr1a [-v path_host:path_container] kunlun-storage /bin/bash start_storage.sh \
    # 237d8a1c-39ec-11eb-92aa-7364f9a0e147 mgr1a mgr1a,mgr1b,mgr1c 1 true cluster_id shard_id
    cmdpat= "sudo docker run %s -itd --network %s --name %s -h %s %s kunlun-storage /bin/bash start_storage_nomgr.sh no_rep %s %d %s %s"
    if usemgr:
        cmdpat= "sudo docker run %s -itd --network %s --name %s -h %s %s kunlun-storage /bin/bash start_storage.sh %s %s %s %d %s %s %s %s"
    waitcmdpat="sudo docker exec %s /bin/bash /kunlun/wait_storage_up.sh"
    shard_id = "meta"
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
            if usemgr:
	        addToCommandsList(commandslist, node['hostip'], targetdir,
		    cmdpat % (node['dockeropts'], network, node['ip'], node['ip'], mountarg, uuid,
		        node['ip'], iplist, i, str(node['is_primary']).lower(), buf, cluster_name, shard_id))
            else:
	        addToCommandsList(commandslist, node['hostip'], targetdir,
		    cmdpat % (node['dockeropts'], network, node['ip'], node['ip'], mountarg, buf, i, cluster_name, shard_id))
	    addToCommandsList(priwaitlist, node['hostip'], targetdir,	waitcmdpat % (node['ip']))
	else:
            if usemgr:
	        addToCommandsList(secmdlist, node['hostip'], targetdir,
		    cmdpat % (node['dockeropts'], network, node['ip'], node['ip'], mountarg, uuid,
		        node['ip'], iplist, i, str(node['is_primary']).lower(), buf, cluster_name, shard_id))
            else:
	        addToCommandsList(secmdlist, node['hostip'], targetdir,
		    cmdpat % (node['dockeropts'], network, node['ip'], node['ip'], mountarg, buf, cluster_name, shard_id))
	    addToCommandsList(sewaitlist, node['hostip'], targetdir, waitcmdpat % (node['ip']))
	del node['hostip']
	del node['is_primary']
	del node['buf']
	del node['orig']
        del node['dockeropts']
	i+=1
    if usemgr:
        pg_metaname = 'docker-meta.json'
    else:
        pg_metaname = 'docker-meta-nomgr.json'
    metaf = open(pg_metaname, 'w')
    json.dump(metanodes, metaf, indent=4)
    metaf.close()

    # Data nodes
    datas = cluster['data']
    datanodes = []
    i = 1
    for shard in datas:
        shard_id = "shard%d" % i
	shardname="%s.shard%s" % (namespace, i)
	nodes=[]
	nodelist=[]
	j=1
        for node in shard['nodes']:
	    bufsize=node.get('innodb_buffer_pool_size', "")
	    name="%s_%d" % (shardname, j)
	    nodeobj={"port":3306, "user":"pgx", "password":"pgx_pwd", "ip":name,
		"hostip":node['ip'], "is_primary":node.get('is_primary', False),
		"buf":node.get('innodb_buffer_pool_size', defbufstr), "orig":node,
                "dockeropts": node.get('dockeropts', args.default_dockeropts)}
	    nodelist.append(name)
	    nodes.append(nodeobj)
	    addIpToMachineMap(machines, node['ip'], args)
	    j += 1
	j=1
	iplist=",".join(nodelist)
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
                if usemgr:
		    addToCommandsList(commandslist, node['hostip'], targetdir,
		        cmdpat % (node['dockeropts'], network, node['ip'], node['ip'], mountarg, uuid,
			    node['ip'], iplist, i, str(node['is_primary']).lower(), buf, cluster_name, shard_id))
                else:
		    addToCommandsList(commandslist, node['hostip'], targetdir,
		        cmdpat % (node['dockeropts'], network, node['ip'], node['ip'], mountarg, buf, i, cluster_name, shard_id))
		addToCommandsList(priwaitlist, node['hostip'], targetdir, waitcmdpat % (node['ip']))
	    else:
                if usemgr:
		    addToCommandsList(secmdlist, node['hostip'], targetdir,
		        cmdpat % (node['dockeropts'], network, node['ip'], node['ip'], mountarg, uuid,
			    node['ip'], iplist, i, str(node['is_primary']).lower(), buf, cluster_name, shard_id))
                else:
		    addToCommandsList(secmdlist, node['hostip'], targetdir,
		        cmdpat % (node['dockeropts'], network, node['ip'], node['ip'], mountarg, buf, i, cluster_name, shard_id))
		addToCommandsList(sewaitlist, node['hostip'], targetdir, waitcmdpat % (node['ip']))
	    del node['hostip']
	    del node['is_primary']
	    del node['buf']
	    del node['orig']
            del node['dockeropts']
	    j+=1
	shard_obj={"shard_name":shardname, "shard_nodes":nodes}
	datanodes.append(shard_obj)
	i+=1
    commandslist.extend(priwaitlist)
    commandslist.extend(secmdlist)
    commandslist.extend(sewaitlist)

    if usemgr:
        pg_shardname = 'docker-shards.json'
    else:
        pg_shardname = 'docker-shards-nomgr.json'
    shardf = open(pg_shardname, 'w')
    json.dump(datanodes, shardf, indent=4)
    shardf.close()
    
    # Comp nodes
    comps = cluster['comp']['nodes']
    compnodes=[]
    # sudo docker run -itd --network klnet --name comp1 -h comp1 -p 6401:5432 [-v path_host:path_container] kunlun-server /bin/bash start_server.sh 1
    cmdpat=r'sudo docker run %s -itd --network %s --name %s -h %s -p %d:5432 %s kunlun-server /bin/bash start_server.sh %s "%s" %d'
    waitcmdpat="sudo docker exec %s /bin/bash /kunlun/wait_server_up.sh"
    waitlist=[]
    i=1
    comp1=None
    comp1ip = None
    isfirst=True
    for node in comps:
	targetdir="."
	localport=node['port']
	localip=node['ip']
        dockeropts = node.get('dockeropts', args.default_dockeropts)
	name="%s.comp%d" % (namespace, i)
	comp={"id":i, "user":node['user'], "password":node['password'],
	    "name":name, "ip":name, "port":5432}
	compnodes.append(comp)
	mountarg=""
	if node.has_key(compdataattr):
	    mountarg = "-v %s:%s" % (node[compdataattr], compdatadir)
	addToCommandsList(commandslist, localip, targetdir,
	    cmdpat % (dockeropts, network, name, name, node['port'], mountarg, node['user'], node['password'], i))
	addToCommandsList(waitlist, localip, targetdir,  waitcmdpat % (name))
	addIpToMachineMap(machines, node['ip'], args)
	if isfirst:
	    isfirst = False
	    comp1 = comp
	    comp1ip = localip
	i+=1
    commandslist.extend(waitlist)

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
    cmdpat = "sudo docker exec %s /bin/bash /kunlun/init_cluster.sh no_rep %s" 
    if usemgr:
        cmdpat = "sudo docker exec %s /bin/bash /kunlun/init_cluster.sh mgr %s"
    addToCommandsList(commandslist, comp1ip, targetdir, cmdpat % (comp1['name'], cluster_name))

    # clustermgr
    targetdir="."
    name="%s.clustermgr" % namespace
    addIpToMachineMap(machines, cluster['clustermgr']['ip'], args)
    dockeropts = cluster['clustermgr'].get('dockeropts', args.default_dockeropts)
    cmdpat="sudo docker run %s -itd --network %s --name %s -h %s kunlun-cluster-manager /bin/bash /kunlun/start_cluster_manager.sh %s"
    addToCommandsList(commandslist, cluster['clustermgr']['ip'], targetdir,
	    cmdpat % (dockeropts, network, name, name, metanodes[0]['ip']))

    haproxy = cluster.get("haproxy", None)
    if haproxy is not None:
        addIpToMachineMap(machines, haproxy['ip'], args)
        generate_haproxy_config(jscfg, machines, 'haproxy.cfg')
        cmdpat = r'haproxy-2.5.0-bin/sbin/haproxy -f haproxy.cfg >& haproxy.log'
        addToCommandsList(commandslist, haproxy['ip'], machines[haproxy['ip']]['basedir'], cmdpat)

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
	files=['kunlun-storage.tar.gz', 'kunlun-server.tar.gz', 'kunlun-cluster-manager.tar.gz']
        if cluster.has_key('haproxy'):
            files.extend(['haproxy-2.5.0-bin.tar.gz', 'haproxy.cfg'])
	if ip == comp1ip:
	    files.extend([pg_metaname, pg_shardname, pg_compname])
	for f in files:
	    comstr = "bash dist.sh --hosts=%s --user=%s %s %s\n"
	    tup= (ip, mach['user'], f, mach['basedir'])
	    comf.write(comstr % tup)
	comstr = "bash remote_run.sh --user=%s %s 'cd %s || exit 1 ; sudo docker inspect %s >& /dev/null || ( gzip -cd %s.tar.gz | sudo docker load )'\n"
	comf.write(comstr % (mach['user'], ip, mach['basedir'], 'kunlun-cluster-manager', 'kunlun-cluster-manager'))
	comf.write(comstr % (mach['user'], ip, mach['basedir'], 'kunlun-server', 'kunlun-server'))
	comf.write(comstr % (mach['user'], ip, mach['basedir'], 'kunlun-storage', 'kunlun-storage'))
        if cluster.has_key('haproxy'):
	    comstr = "bash remote_run.sh --user=%s %s 'cd %s || exit 1 ; tar -xzf haproxy-2.5.0-bin.tar.gz'\n"
	    comf.write(comstr % (mach['user'], ip, mach['basedir']))

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
    namespace = cluster.get('namespace', args.namespace)
    meta = cluster['meta']

    cmdpat= "sudo docker container start %s"
    waitcmdpat="sudo docker exec %s /bin/bash /kunlun/wait_storage_up.sh"
    targetdir = "/"
    # Meta nodes
    i=1
    for node in meta['nodes']:
	name="%s.meta%s" % (namespace, i)
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % name)
	addToCommandsList(waitlist, node['ip'], targetdir, waitcmdpat % name)
	addIpToMachineMap(machines, node['ip'], args)
	i+=1

    # Data nodes
    datas = cluster['data']
    i = 1
    for shard in datas:
	shardname="%s.shard%s" % (namespace, i)
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
    name="%s.clustermgr" % namespace
    addIpToMachineMap(machines, cluster['clustermgr']['ip'], args)
    addToCommandsList(commandslist, cluster['clustermgr']['ip'], targetdir, cmdpat % name)

    # Comp nodes
    comps = cluster['comp']['nodes']
    waitcmdpat="sudo docker exec %s /bin/bash /kunlun/wait_server_up.sh"
    i=1
    for node in comps:
	localip=node['ip']
	name="%s.comp%d" % (namespace, i)
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % name)
	addToCommandsList(waitlist, node['ip'], targetdir, waitcmdpat % name)
	i+=1
    commandslist.extend(waitlist)

    haproxy = cluster.get("haproxy", None)
    if haproxy is not None:
        addIpToMachineMap(machines, haproxy['ip'], args)
        cmdpat = r'haproxy-2.5.0-bin/sbin/haproxy -f haproxy.cfg >& haproxy.log'
        addToCommandsList(commandslist, haproxy['ip'], machines[haproxy['ip']]['basedir'], cmdpat)

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
    namespace = cluster.get('namespace', args.namespace)
    meta = cluster['meta']

    haproxy = cluster.get("haproxy", None)
    if haproxy is not None:
        addIpToMachineMap(machines, haproxy['ip'], args)
        cmdpat="cat haproxy.pid | xargs kill -9"
        addToCommandsList(commandslist, haproxy['ip'], machines[haproxy['ip']]['basedir'], cmdpat)

    cmdpat= "sudo docker container stop %s"
    targetdir = "/"
    # Meta nodes
    i=1
    for node in meta['nodes']:
	name="%s.meta%s" % (namespace, i)
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % name)
	addIpToMachineMap(machines, node['ip'], args)
	i+=1

    # Data nodes
    datas = cluster['data']
    i = 1
    for shard in datas:
	shardname="%s.shard%s" % (namespace, i)
	j=1
        for node in shard['nodes']:
	    name="%s_%d" % (shardname, j)
	    addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % name)
	    addIpToMachineMap(machines, node['ip'], args)
	    j += 1
	i += 1

    # clustermgr
    name="%s.clustermgr" % namespace
    addIpToMachineMap(machines, cluster['clustermgr']['ip'], args)
    addToCommandsList(commandslist, cluster['clustermgr']['ip'], targetdir, cmdpat % name)

    # Comp nodes
    comps = cluster['comp']['nodes']
    i=1
    for node in comps:
	localip=node['ip']
	name="%s.comp%d" % (namespace, i)
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
    namespace = cluster.get('namespace', args.namespace)
    meta = cluster['meta']

    haproxy = cluster.get("haproxy", None)
    if haproxy is not None:
        addIpToMachineMap(machines, haproxy['ip'], args)
        cmdpat="cat haproxy.pid | xargs kill -9"
        addToCommandsList(commandslist, haproxy['ip'], machines[haproxy['ip']]['basedir'], cmdpat)
        cmdpat="rm -f haproxy.pid"
        addToCommandsList(commandslist, haproxy['ip'], machines[haproxy['ip']]['basedir'], cmdpat)

    cmdpat= "sudo docker container rm -fv %s"
    rmcmdpat = "sudo rm -fr %s"
    targetdir = "/"
    # Meta nodes
    i=1
    for node in meta['nodes']:
	name="%s.meta%s" % (namespace, i)
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
	shardname="%s.shard%s" % (namespace, i)
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
    name="%s.clustermgr" % namespace
    addIpToMachineMap(machines, cluster['clustermgr']['ip'], args)
    addToCommandsList(commandslist, cluster['clustermgr']['ip'], targetdir, cmdpat % name)

    # Comp nodes
    comps = cluster['comp']['nodes']
    i=1
    for node in comps:
	localip=node['ip']
	name="%s.comp%d" % (namespace, i)
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % name)
	if node.has_key(compdataattr):
	    addToCommandsList(commandslist, node['ip'], targetdir, rmcmdpat % node[compdataattr])
	i+=1

    for ip in machines:
	    mach =machines[ip]
	    cmdpat = 'sudo docker image rm -f %s'
	    addToCommandsList(commandslist, ip, "/", cmdpat % 'kunlun-storage')
	    addToCommandsList(commandslist, ip, "/", cmdpat % 'kunlun-server')
	    addToCommandsList(commandslist, ip, "/", cmdpat % 'kunlun-cluster-manager')
	    cmdpat = 'rm -f %s'
	    addToCommandsList(commandslist, ip, ".", cmdpat % 'kunlun-storage.tar.gz')
	    addToCommandsList(commandslist, ip, ".", cmdpat % 'kunlun-server.tar.gz')
	    addToCommandsList(commandslist, ip, ".", cmdpat % 'kunlun-cluster-manager.tar.gz')

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
    parser.add_argument('--namespace', type=str, help="the default namespace", default='kunlun')
    parser.add_argument('--default_dockeropts', type=str, help="the default docker options", default="")

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
