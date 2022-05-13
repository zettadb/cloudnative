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
import socket
import collections
import copy

def addIpToMachineMap(map, ip, args):
    if not map.has_key(ip):
	mac={"ip":ip, "user":args.defuser, "basedir":args.defbase}
	map[ip] = mac

def addMachineToMap(map, ip, user, basedir):
    # We can add logic here to check if the item exsits, new added should be unique to existing.
    if map.has_key(ip):
        return
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

def addToFileList(files, ip, sourcepath, target):
    lst = [ip, sourcepath, target]
    files.append(lst)

def addToCommandsListNoenv(cmds, ip, targetdir, command):
    lst = [ip, targetdir, command]
    cmds.append(lst)

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

def islocal(args, ip):
    if ip.startswith("127") or ip in [args.localip, "localhost", socket.gethostname()]:
        return True
    return False

def process_filelist(comf, args, machines, filelist):
    for filetup in filelist:
        ip = filetup[0]
        mach = machines[ip]
        if islocal(args, ip):
            # For local, we do not consider the user.
            mkstr = '''/bin/bash -xc $"cp -f %s %s" '''
            tup= (filetup[1], filetup[2])
        else:
            mkstr = '''bash dist.sh --hosts=%s --user=%s %s %s '''
            tup= (ip, mach['user'], filetup[1], filetup[2])
	comf.write(mkstr % tup)
        comf.write("\n")

def process_file(comf, args, machines, ip, source, target):
    process_filelist(comf, args, machines, [[ip, source, target]])

def process_commandslist_noenv(comf, args, machines, commandslist):
    for cmd in commandslist:
	ip=cmd[0]
	mach = machines[ip]
        if islocal(args, ip):
            # For local, we do not consider the user.
            mkstr = '''/bin/bash -xc $"cd %s || exit 1; %s" '''
            tup= (cmd[1], cmd[2])
        else:
            ttyopt=""
            if cmd[2].find("sudo ") >= 0:
                ttyopt="--tty"
            mkstr = '''bash remote_run.sh %s --user=%s %s $"cd %s || exit 1; %s" '''
            tup= (ttyopt, mach['user'], ip, cmd[1], cmd[2])
	comf.write(mkstr % tup)
        comf.write("\n")

def process_command_noenv(comf, args, machines, ip, targetdir, command):
    process_commandslist_noenv(comf, args, machines, [[ip, targetdir, command]])

def process_commandslist_setenv(comf, args, machines, commandslist):
    for cmd in commandslist:
	ip=cmd[0]
	mach = machines[ip]
        if islocal(args, ip):
            # For local, we do not consider the user.
            mkstr = '''/bin/bash -xc $"cd %s && envtype=%s && source ./env.sh && cd %s || exit 1; %s" '''
            tup= (mach['basedir'], cmd[3], cmd[1], cmd[2])
        else:
            ttyopt=""
            if cmd[2].find("sudo ") >= 0:
                ttyopt="--tty"
            mkstr = '''bash remote_run.sh %s --user=%s %s $"cd %s && envtype=%s && source ./env.sh && cd %s || exit 1; %s" '''
            tup= (ttyopt, mach['user'], ip, mach['basedir'], cmd[3], cmd[1], cmd[2])
	comf.write(mkstr % tup)
        comf.write("\n")

def process_command_setenv(comf, args, machines, ip, targetdir, command, envtype='no'):
    process_commandslist_setenv(comf, args, machines, [[ip, targetdir, command, envtype]])

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

def validate_config(jscfg, machines, args):
    meta = jscfg['meta']
    clustermgr = jscfg['cluster_manager']
    nodemgr = jscfg['node_manager']
    ha_mode = meta.get('ha_mode', '')
    portmap = {}
    dirmap = {}

    nodecnt = len(meta['nodes'])
    if ha_mode == '':
        if nodecnt > 1:
            ha_mode = 'mgr'
        else:
            ha_mode = 'no_rep'
    if nodecnt == 0:
        raise ValueError('Error: There must be at least one node in meta shard')
    if nodecnt > 1 and ha_mode == 'no_rep':
        raise ValueError('Error: ha_mode is no_rep, but there are multiple nodes in meta shard')
    elif nodecnt == 1 and ha_mode != 'no_rep':
        raise ValueError('Error: ha_mode is mgr/rbr, but there is only one node in meta shard')
    hasPrimary=False
    for node in meta['nodes']:
        addPortToMachine(portmap, node['ip'], node['port'])
        if node.has_key('xport'):
            addPortToMachine(portmap, node['ip'], node['xport'])
        if node.has_key('mgr_port'):
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
    if nodecnt > 1:
        if not hasPrimary:
            raise ValueError('Error: No primary found in meta shard, there should be one and only one !')
    else:
            node['is_primary'] = True

    for node in clustermgr['nodes']:
        if node.has_key('brpc_raft_port'):
            addPortToMachine(portmap, node['ip'], node['brpc_raft_port'])
        else:
            node['brpc_raft_port'] = args.defbrpc_raft_port_clustermgr
            addPortToMachine(portmap, node['ip'], args.defbrpc_raft_port_clustermgr)
        if node.has_key('brpc_http_port'):
            addPortToMachine(portmap, node['ip'], node['brpc_http_port'])
        else:
            node['brpc_http_port'] = args.defbrpc_http_port_clustermgr
            addPortToMachine(portmap, node['ip'], args.defbrpc_http_port_clustermgr)

    defpaths = {
            "server_datadirs": "server_datadir",
            "storage_datadirs": "storage_datadir",
            "storage_logdirs": "storage_logdir",
            "storage_waldirs": "storage_waldir",
        }
    for node in nodemgr['nodes']:
        mach = machines.get(node['ip'])
        if node.has_key('brpc_http_port'):
            addPortToMachine(portmap, node['ip'], node['brpc_http_port'])
        else:
            node['brpc_http_port'] = args.defbrpc_http_port_nodemgr
            addPortToMachine(portmap, node['ip'], args.defbrpc_http_port_nodemgr)
        # The logic is that:
        # - if it is set, check every item is an absolute path.
        # - if it is not set, it is default to $basedir/{server_datadir, storage_datadir, storage_logdir, storage_waldir}
        for item in ["server_datadirs", "storage_datadirs", "storage_logdirs", "storage_waldirs"]:
            if node.has_key(item):
                nodedirs = node[item].strip()
                for d in nodedirs.split(","):
                    if not d.strip().startswith('/'):
                        raise ValueError('Error: the dir in %s must be absolute path!' % item)
            else:
                node[item] = "%s/%s" % (mach['basedir'], defpaths[item])

def get_ha_mode(jscfg, args):
    meta = jscfg['meta']
    if len(meta['nodes']) > 1:
        return cluster.get('ha_mode', 'mgr')
    else:
        return 'no_rep'

def install_meta_env(comf, mach, machines, args):
    storagedir = "kunlun-storage-%s" % args.product_version
    ip = mach['ip']
    if args.sudo:
        process_command_noenv(comf, args, machines, ip, '/',
            'sudo mkdir -p %s && sudo chown -R %s:\`id -gn %s\` %s' % (mach['basedir'],
            mach['user'], mach['user'], mach['basedir']))
    else:
        process_command_noenv(comf, args, machines, ip, '/', 'mkdir -p %s' % mach['basedir'])
    # Set up the files
    process_file(comf, args, machines, ip, 'clustermgr/%s.tgz' % storagedir, mach['basedir'])
    process_command_noenv(comf, args, machines, ip, mach['basedir'], 'tar -xzf %s.tgz' % storagedir)

	# files
    flist = [
        ['install/build_driver_formysql.sh', '%s/resources' % storagedir],
        ['install/process_deps.sh', '.'],
        ['install/change_config.sh', '.']
        ]
    for fpair in flist:
        process_file(comf, args, machines, ip, fpair[0], "%s/%s" % (mach['basedir'], fpair[1]))

    # Set up the env.sh, this must be before 'process_command_setenv'
    process_file(comf, args, machines, ip, 'env.sh.template', mach['basedir'])
    extstr = "sed -s 's#KUNLUN_BASEDIR#%s#g' env.sh.template > env.sh" % mach['basedir']
    process_command_noenv(comf, args, machines, ip, mach['basedir'], extstr)
    extstr = "sed -i 's#KUNLUN_VERSION#%s#g' env.sh" % args.product_version
    process_command_noenv(comf, args, machines, ip, mach['basedir'], extstr)

    comstr = "bash ../../process_deps.sh"
    process_command_setenv(comf, args, machines, ip, "%s/lib" % storagedir, comstr, "storage")

    comstr = "bash build_driver_formysql.sh"
    process_command_setenv(comf, args, machines, ip, "%s/resources" % storagedir, comstr, "storage")
 
    comstr = "cd %s || exit 1; test -d etc && echo > etc/instances_list.txt 2>/dev/null; exit 0" % storagedir
    process_command_noenv(comf, args, machines, ip, mach['basedir'], comstr)

def install_nodemgr_env(comf, mach, machines, args):
    progname = "kunlun-node-manager-%s" % args.product_version
    ip = mach['ip']
    if args.sudo:
        process_command_noenv(comf, args, machines, ip, '/',
            'sudo mkdir -p %s && sudo chown -R %s:\`id -gn %s\` %s' % (mach['basedir'],
            mach['user'], mach['user'], mach['basedir']))
    else:
        process_command_noenv(comf, args, machines, ip, '/', 'mkdir -p %s' % mach['basedir'])
    # Set up the files
    process_file(comf, args, machines, ip, 'install/change_config.sh', mach['basedir'])
    process_file(comf, args, machines, ip, 'clustermgr/%s.tgz' % progname, mach['basedir'])
    process_command_noenv(comf, args, machines, ip, mach['basedir'], 'tar -xzf %s.tgz' % progname)
    process_command_noenv(comf, args, machines, ip, mach['basedir'], 'touch env.sh')

def install_clustermgr_env(comf, mach, machines, args):
    progname = "kunlun-cluster-manager-%s" % args.product_version
    ip = mach['ip']
    if args.sudo:
        process_command_noenv(comf, args, machines, ip, '/',
            'sudo mkdir -p %s && sudo chown -R %s:\`id -gn %s\` %s' % (mach['basedir'],
            mach['user'], mach['user'], mach['basedir']))
    else:
        process_command_noenv(comf, args, machines, ip, '/', 'mkdir -p %s' % mach['basedir'])
    # Set up the files
    process_file(comf, args, machines, ip, 'install/change_config.sh', mach['basedir'])
    process_file(comf, args, machines, ip, 'clustermgr/%s.tgz' % progname, mach['basedir'])
    process_command_noenv(comf, args, machines, ip, mach['basedir'], 'tar -xzf %s.tgz' % progname)
    process_command_noenv(comf, args, machines, ip, mach['basedir'], 'touch env.sh')

def setup_machines(jscfg, machines, args):
    machnodes = jscfg.get('machines', [])
    meta = jscfg.get('meta', {"nodes": []})
    nodemgr = jscfg.get('node_manager', {"nodes": []})
    clustermgr = jscfg.get('cluster_manager', {"nodes": []})
    for mach in machnodes:
	ip=mach['ip']
	user=mach.get('user', args.defuser)
	base=mach.get('basedir', args.defbase)
	addMachineToMap(machines, ip, user, base)
    for node in meta['nodes']:
        addIpToMachineMap(machines, node['ip'], args)
    for node in nodemgr['nodes']:
        addIpToMachineMap(machines, node['ip'], args)
    for node in clustermgr['nodes']:
        addIpToMachineMap(machines, node['ip'], args)

def install_clustermgr(args):
    conf = open(args.config)
    jscfg = json.loads(conf.read(), object_pairs_hook=collections.OrderedDict)
    machines = {}
    setup_machines(jscfg, machines, args)
    validate_config(jscfg, machines, args)
    comf = open(r'clustermgr/install.sh', 'w')
    comf.write('#! /bin/bash\n')
    install_with_config(jscfg, comf, machines, args)
    comf.close()

def clean_clustermgr(args):
    conf = open(args.config)
    jscfg = json.loads(conf.read(), object_pairs_hook=collections.OrderedDict)
    machines = {}
    setup_machines(jscfg, machines, args)
    validate_config(jscfg, machines, args)
    comf = open(r'clustermgr/clean.sh', 'w')
    comf.write('#! /bin/bash\n')
    clean_with_config(jscfg, comf, machines, args)
    comf.close()

def getuuid():
    return str(uuid.uuid1())

def install_with_config(jscfg, comf, machines, args):
    meta = jscfg['meta']
    clustermgr = jscfg['cluster_manager']
    nodemgr = jscfg['node_manager']
    ha_mode = meta.get('ha_mode', '')
    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version
    nodemgrdir = "kunlun-node-manager-%s" % args.product_version
    sudopfx=""
    if args.sudo:
        sudopfx="sudo "

    filesmap = {}
    commandslist = []
    dirmap = {}
    cluster_name = 'meta'
    extraopt = " --ha_mode=%s" % ha_mode

    # used for install storage nodes
    if not meta.has_key('group_uuid'):
	    meta['group_uuid'] = getuuid()
    my_metaname = 'mysql_meta.json'
    metaf = open(r'clustermgr/%s' % my_metaname,'w')
    json.dump(meta, metaf, indent=4)
    metaf.close()

    # used for bootstrap
    reg_metaname = 'reg_meta.json'
    metaf = open(r'clustermgr/%s' % reg_metaname, 'w')
    objs = []
    for node in meta['nodes']:
	obj = {}
	obj['is_primary'] = node.get('is_primary', False)
        obj['data_dir_path'] = node['data_dir_path']
	obj['ip'] = node['ip']
	obj['port'] = node['port']
	obj['user'] = "pgx"
	obj['password'] = "pgx_pwd"
	objs.append(obj)
    json.dump(objs, metaf, indent=4)
    metaf.close()

    cmdpat = '%spython2 install-mysql.py --config=./%s --target_node_index=%d --cluster_id=%s --shard_id=%s'
    if args.small:
        cmdpat += ' --dbcfg=./template-small.cnf'
    # commands like:
    # python2 install-mysql.py --config=./mysql_meta.json --target_node_index=0
    targetdir='%s/dba_tools' % storagedir
    shard_id = 'meta'
    pries = []
    secs = []
    meta_addrs = []
    i = 0 
    metaips = set()
    for node in meta['nodes']:
        metaips.add(node['ip'])
	meta_addrs.append("%s:%s" % (node['ip'], str(node['port'])))
	addNodeToFilesMap(filesmap, node, reg_metaname, targetdir)
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

    for item in pries:
        addToCommandsList(commandslist, item[0], item[1], item[2] + extraopt)
    for item in secs:
        addToCommandsList(commandslist, item[0], item[1], item[2] + extraopt)

    # bootstrap the cluster
    firstmeta = meta['nodes'][0]
    targetdir='%s/dba_tools' % storagedir
    cmdpat=r'python2 bootstrap.py --config=./%s --bootstrap_sql=./meta_inuse.sql' + extraopt
    addToCommandsList(commandslist, firstmeta['ip'], targetdir, cmdpat % reg_metaname, "storage")
    nodemgrsql = 'nodemgr.sql'
    sqlf = open('clustermgr/%s' % nodemgrsql, 'w')
    for node in nodemgr['nodes']:
        sqlf.write("insert into kunlun_metadata_db.server_nodes(hostaddr, comp_datadir, datadir, logdir, wal_log_dir) values('%s','%s','%s','%s','%s');\n" %
                (node['ip'], node['server_datadirs'], node['storage_datadirs'], node['storage_logdirs'], node['storage_waldirs']))
    sqlf.close()
    addNodeToFilesMap(filesmap, firstmeta, nodemgrsql, targetdir)
    cmdpat = "mysql -h%s -P %s -upgx -ppgx_pwd < %s"
    addToCommandsList(commandslist, firstmeta['ip'], targetdir, cmdpat % (firstmeta['ip'], str(firstmeta['port']), nodemgrsql), "storage")

    metaseeds=",".join(meta_addrs)
    cmdpat = "bash change_config.sh %s '%s' '%s'"
    nodemgrips = set()
    for node in nodemgr['nodes']:
        confpath = "%s/conf/node_mgr.cnf" % nodemgrdir
        addIpToMachineMap(machines, node['ip'], args)
        nodemgrips.add(node['ip'])
        mach = machines.get(node['ip'])
        for item in ["server_datadirs", "storage_datadirs", "storage_logdirs", "storage_waldirs"]:
            nodedirs = node[item].strip()
            for d in nodedirs.split(","):
                addToDirMap(dirmap, node['ip'], d.strip())
        targetdir = "program_binaries"
        addToDirMap(dirmap, node['ip'], "%s/%s" % (mach['basedir'], targetdir))
        addToDirMap(dirmap, node['ip'], "%s/%s/util" % (mach['basedir'], targetdir))
        addToDirMap(dirmap, node['ip'], "%s/instance_binaries" % mach['basedir'])
        addNodeToFilesMap(filesmap, node, "%s.tgz" % storagedir, targetdir)
        addNodeToFilesMap(filesmap, node, "%s.tgz" % storagedir, targetdir)
        addNodeToFilesMap(filesmap, node, "hadoop-3.3.1.tar.gz", targetdir)
        addNodeToFilesMap(filesmap, node, "jdk-8u131-linux-x64.tar.gz", targetdir)
        addNodeToFilesMap(filesmap, node, "prometheus.tgz", targetdir)
        addNodeToFilesMap(filesmap, node, "backup", "%s/util" % targetdir)
        addNodeToFilesMap(filesmap, node, "restore", "%s/util" % targetdir)
        addNodeToFilesMap(filesmap, node, "xtrabackup", "%s/util" % targetdir)
        addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf hadoop-3.3.1.tar.gz")
        addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf jdk-8u131-linux-x64.tar.gz")
        addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf prometheus.tgz")
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (confpath, 'meta_group_seeds', metaseeds))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (confpath, 'brpc_http_port', node['brpc_http_port']))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (confpath, 'local_ip', node['ip']))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (confpath, 'program_binaries_path', '%s/program_binaries' % mach['basedir']))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (confpath, 'instance_binaries_path', '%s/instance_binaries' % mach['basedir']))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (confpath, 'prometheus_path', '%s/program_binaries/prometheus' % mach['basedir']))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (confpath, 'storage_prog_package_name', storagedir))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (confpath, 'computer_prog_package_name', serverdir))
        addToCommandsList(commandslist, node['ip'], "%s/bin" % nodemgrdir, "bash start_node_mgr.sh </dev/null >& run.log &")


    clustermgrips = set()
    members=[]
    for node in clustermgr['nodes']:
        members.append("%s:%d:0" % (clustermgr['nodes'][0]['ip'], clustermgr['nodes'][0]['brpc_raft_port']))
    initmember = "%s," % ",".join(members)
    cmdpat = "bash change_config.sh %s '%s' '%s'"
    confpath = "%s/conf/cluster_mgr.cnf" % clustermgrdir
    for node in clustermgr['nodes']:
        addIpToMachineMap(machines, node['ip'], args)
        clustermgrips.add(node['ip'])
        mach = machines.get(node['ip'])
        targetdir = "program_binaries"
        addToDirMap(dirmap, node['ip'], "%s/%s" % (mach['basedir'], targetdir))
        addToDirMap(dirmap, node['ip'], "%s/instance_binaries" % mach['basedir'])
        addNodeToFilesMap(filesmap, node, "%s.tgz" % storagedir, targetdir)
        addNodeToFilesMap(filesmap, node, "%s.tgz" % serverdir, targetdir)
        addNodeToFilesMap(filesmap, node, "prometheus.tgz", targetdir)
        addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf prometheus.tgz")
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (confpath, 'meta_group_seeds', metaseeds))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (confpath, 'brpc_raft_port', node['brpc_raft_port']))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (confpath, 'brpc_http_port', node['brpc_http_port']))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (confpath, 'local_ip', node['ip']))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (confpath, 'raft_group_member_init_config', initmember))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (confpath, 'program_binaries_path', '%s/program_binaries' % mach['basedir']))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (confpath, 'instance_binaries_path', '%s/instance_binaries' % mach['basedir']))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (confpath, 'prometheus_path', '%s/program_binaries/prometheus' % mach['basedir']))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (confpath, 'storage_prog_package_name', storagedir))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (confpath, 'computer_prog_package_name', serverdir))
        addToCommandsList(commandslist, node['ip'], "%s/bin" % clustermgrdir, "bash start_cluster_mgr.sh </dev/null >& start.log &")

   # setup env for meta
    for ip in metaips:
        mach = machines.get(ip)
        install_meta_env(comf, mach, machines, args)

   # setup env for nodemgr
    for ip in nodemgrips:
        mach = machines.get(ip)
        install_nodemgr_env(comf, mach, machines, args)

   # setup env for nodemgr
    for ip in clustermgrips:
        mach = machines.get(ip)
        install_clustermgr_env(comf, mach, machines, args)

    # dir making
    for ip in dirmap:
	mach = machines.get(ip)
	dirs=dirmap[ip]
	for d in dirs:
            if args.sudo:
                process_command_noenv(comf, args, machines, ip, '/',
                    'sudo mkdir -p %s && sudo chown -R %s:\`id -gn %s\` %s' % (d, mach['user'], mach['user'], d))
            else:
                process_command_noenv(comf, args, machines, ip, '/', 'mkdir -p %s' % d)

    # files copy.
    for ip in filesmap:
	mach = machines.get(ip)
	fmap = filesmap[ip]
	for fname in fmap:
            process_file(comf, args, machines, ip, 'clustermgr/%s' % fname, '%s/%s' % (mach['basedir'], fmap[fname]))

    # The reason for not using commands map is that, we need to keep the order for the commands.
    process_commandslist_setenv(comf, args, machines, commandslist)

def clean_with_config(jscfg, comf, machines, args):
    meta = jscfg['meta']
    clustermgr = jscfg['cluster_manager']
    nodemgr = jscfg['node_manager']
    storagedir = "kunlun-storage-%s" % args.product_version
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version
    nodemgrdir = "kunlun-node-manager-%s" % args.product_version
    sudopfx=""
    if args.sudo:
        sudopfx="sudo "

    filesmap = {}
    commandslist = []
    dirmap = {}

    # clean the meta nodes
    targetdir='%s/dba_tools' % storagedir
    for node in meta['nodes']:
	addIpToMachineMap(machines, node['ip'], args)
	cmdpat = r'bash stopmysql.sh %d'
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'], "storage")
	cmdpat = r'%srm -fr %s'
	addToCommandsList(commandslist, node['ip'], ".", cmdpat % (sudopfx, node['log_dir_path']))
	addToCommandsList(commandslist, node['ip'], ".", cmdpat % (sudopfx, node['data_dir_path']))
	if node.has_key('innodb_log_dir_path'):
		addToCommandsList(commandslist, node['ip'], ".", cmdpat % (sudopfx, node['innodb_log_dir_path']))

    # stop the nodemgr processes
    for node in nodemgr['nodes']:
	addIpToMachineMap(machines, node['ip'], args)
        addToCommandsList(commandslist, node['ip'], "%s/bin" % nodemgrdir, "bash stop_node_mgr.sh")
        for item in ["server_datadirs", "storage_datadirs", "storage_logdirs", "storage_waldirs"]:
            nodedirs = node[item].strip()
            for d in nodedirs.split(","):
                cmdpat = '%srm -fr %s/*'
                addToCommandsList(commandslist, node['ip'], "/", cmdpat % (sudopfx, d))

    # stop the nodemgr processes
    for node in clustermgr['nodes']:
        addIpToMachineMap(machines, node['ip'], args)
        addToCommandsList(commandslist, node['ip'], "%s/bin" % clustermgrdir, "bash stop_cluster_mgr.sh")

    for ip in machines:
	mach =machines[ip]
        cmdpat = '%srm -fr %s/*'
        addToCommandsList(commandslist, ip, ".", cmdpat % (sudopfx, mach['basedir']))

    process_commandslist_setenv(comf, args, machines, commandslist)

def checkdirs(dirs):
    for d in dirs:
	if not os.path.exists(d):
	    os.mkdir(d)

if  __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Specify the arguments.')
    actions=["install", "clean"]
    parser.add_argument('--config', type=str, help="The config path", required=True)
    parser.add_argument('--action', type=str, help="The action", default='install', choices=actions)
    parser.add_argument('--defuser', type=str, help="the command", default=getpass.getuser())
    parser.add_argument('--defbase', type=str, help="the command", default='/kunlun')
    parser.add_argument('--sudo', help="whether to use sudo", default=False, action='store_true')
    parser.add_argument('--product_version', type=str, help="kunlun version", default='0.9.2')
    parser.add_argument('--localip', type=str, help="The local ip address", default='127.0.0.1')
    parser.add_argument('--small', help="whether to use small template", default=False, action='store_true')
    parser.add_argument('--defbrpc_raft_port_clustermgr', type=int, help="default brpc_raft_port for cluster_manager", default=58001)
    parser.add_argument('--defbrpc_http_port_clustermgr', type=int, help="default brpc_http_port for cluster_manager", default=58000)
    parser.add_argument('--defbrpc_http_port_nodemgr', type=int, help="default brpc_http_port for node_manager", default=58002)

    args = parser.parse_args()
    if not args.defbase.startswith('/'):
        raise ValueError('Error: the default basedir must be absolute path!')

    print str(sys.argv)
    checkdirs(['clustermgr'])
    if args.action == 'install':
        install_clustermgr(args)
    elif args.action == 'clean':
        clean_clustermgr(args)
    else:
        # just defensive, for more more actions later.
        pass
