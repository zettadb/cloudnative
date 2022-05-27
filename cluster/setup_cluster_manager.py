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
	map[ip] = []
    tlist = map[ip]
    tlist.append([fname, targetdir])

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

def set_metapath_using_nodemgr(machines, nodem, noden):
    nodem['data_dir_path'] = "%s/instance_data/data_dir_path/%s" % (noden['storage_datadirs'].split(",")[0], str(nodem['port']))
    nodem['log_dir_path'] = "%s/instance_data/log_dir_path/%s" % (noden['storage_logdirs'].split(",")[0], str(nodem['port']))
    nodem['innodb_log_dir_path'] = "%s/instance_data/innodb_log_dir_path/%s" % (noden['storage_waldirs'].split(",")[0], str(nodem['port']))
    mach = machines.get(nodem['ip'])
    nodem['program_dir'] = "instance_binaries/storage/%s" % str(nodem['port'])
    nodem['user'] = mach['user']

def generate_storage_service(args, machines, commandslist, node, idx, filesmap):
    mach = machines.get(node['ip'])
    storagedir = "kunlun-storage-%s" % args.product_version
    fname = "%d-kunlun-storage-%d.service" % (idx, node['port'])
    servname = "kunlun-storage-%d" % node['port']
    fname_to = "kunlun-storage-%d.service" % node['port']
    servicef = open('clustermgr/%s' % fname, 'w')
    servicef.write("# kunlun-storage-%d systemd service file\n\n" % node['port'])
    servicef.write("[Unit]\n")
    servicef.write("Description=kunlun-storage-%d\n" % node['port'])
    servicef.write("After=network.target\n\n")
    servicef.write("[Install]\n")
    servicef.write("WantedBy=multi-user.target\n\n")
    servicef.write("[Service]\n")
    servicef.write("Type=forking\n")
    servicef.write("User=%s\n" % mach['user'])
    servicef.write("Restart=on-failure\n")
    servicef.write("WorkingDirectory=%s/instance_binaries/storage/%s/%s/dba_tools\n" % (mach['basedir'], str(node['port']), storagedir))
    servicef.write("ExecStart=/bin/bash startmysql.sh %d\n" % (node['port']))
    servicef.write("ExecStop=/bin/bash stopmysql.sh %d\n" % (node['port']))
    servicef.close()
    addNodeToFilesMap(filesmap, node, fname, './%s' % fname_to)
    addToCommandsList(commandslist, node['ip'], '.', "sudo cp -f %s /usr/lib/systemd/system/" % fname_to)
    addToCommandsList(commandslist, node['ip'], '.', "sudo systemctl enable %s" % servname)

def generate_clustermgr_service(args, machines, commandslist, node, idx, filesmap):
    mach = machines.get(node['ip'])
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version
    fname = "%d-kunlun-cluster-manager-%d.service" % (idx, node['brpc_raft_port'])
    servname = "kunlun-cluster-manager-%d" % node['brpc_raft_port']
    fname_to = "kunlun-cluster-manager-%d.service" % node['brpc_raft_port']
    servicef = open('clustermgr/%s' % fname, 'w')
    servicef.write("# kunlun-cluster-manager-%d systemd service file\n\n" % node['brpc_raft_port'])
    servicef.write("[Unit]\n")
    servicef.write("Description=kunlun-cluster-manager-%d\n" % node['brpc_raft_port'])
    servicef.write("After=network.target\n\n")
    servicef.write("[Install]\n")
    servicef.write("WantedBy=multi-user.target\n\n")
    servicef.write("[Service]\n")
    servicef.write("Type=forking\n")
    servicef.write("User=%s\n" % mach['user'])
    servicef.write("Restart=on-failure\n")
    servicef.write("WorkingDirectory=%s/%s/bin\n" % (mach['basedir'], clustermgrdir))
    servicef.write("ExecStart=/bin/bash start_cluster_mgr.sh\n")
    servicef.write("ExecStop=/bin/bash stop_cluster_mgr.sh\n")
    servicef.close()
    addNodeToFilesMap(filesmap, node, fname, './%s' % fname_to)
    addToCommandsList(commandslist, node['ip'], '.', "sudo cp -f %s /usr/lib/systemd/system/" % fname_to)
    addToCommandsList(commandslist, node['ip'], '.', "sudo systemctl enable %s" % servname)

def generate_nodemgr_service(args, machines, commandslist, node, idx, filesmap):
    mach = machines.get(node['ip'])
    nodemgrdir = "kunlun-node-manager-%s" % args.product_version
    fname = "%d-kunlun-node-manager-%d.service" % (idx, node['brpc_http_port'])
    servname = "kunlun-node-manager-%d" % node['brpc_http_port']
    fname_to = "kunlun-node-manager-%d.service" % node['brpc_http_port']
    servicef = open('clustermgr/%s' % fname, 'w')
    servicef.write("# kunlun-node-manager-%d systemd service file\n\n" % node['brpc_http_port'])
    servicef.write("[Unit]\n")
    servicef.write("Description=kunlun-node-manager-%d\n" % node['brpc_http_port'])
    servicef.write("After=network.target\n\n")
    servicef.write("[Install]\n")
    servicef.write("WantedBy=multi-user.target\n\n")
    servicef.write("[Service]\n")
    servicef.write("Type=forking\n")
    servicef.write("User=%s\n" % mach['user'])
    servicef.write("Restart=on-failure\n")
    servicef.write("WorkingDirectory=%s/%s/bin\n" % (mach['basedir'], nodemgrdir))
    servicef.write("ExecStart=/bin/bash start_node_mgr.sh\n")
    servicef.write("ExecStop=/bin/bash stop_node_mgr.sh\n")
    servicef.close()
    addNodeToFilesMap(filesmap, node, fname, './%s' % fname_to)
    addToCommandsList(commandslist, node['ip'], '.', "sudo cp -f %s /usr/lib/systemd/system/" % fname_to)
    addToCommandsList(commandslist, node['ip'], '.', "sudo systemctl enable %s" % servname)

def validate_config(jscfg, machines, args):
    meta = jscfg.get('meta', {'nodes':[]})
    if not meta.has_key('nodes'):
        meta['nodes'] = []
    clustermgr = jscfg.get('cluster_manager', {'nodes':[]})
    if not clustermgr.has_key('nodes'):
        clustermgr['nodes'] = []
    nodemgr = jscfg.get('node_manager', {'nodes':[]})
    if not nodemgr.has_key('nodes'):
        nodemgr['nodes'] = []
    ha_mode = meta.get('ha_mode', '')
    portmap = {}
    dirmap = {}

    nodecnt = len(meta['nodes'])
    if ha_mode == '':
        if nodecnt > 1:
            ha_mode = 'mgr'
        else:
            ha_mode = 'no_rep'
    if nodecnt == 0 and not meta.has_key('group_seeds'):
        raise ValueError('Error: There must be at least one node in meta shard')
    if nodecnt > 1 and ha_mode == 'no_rep':
        raise ValueError('Error: ha_mode is no_rep, but there are multiple nodes in meta shard')
    elif nodecnt == 1 and ha_mode != 'no_rep':
        raise ValueError('Error: ha_mode is mgr/rbr, but there is only one node in meta shard')
    hasPrimary=False
    for node in meta['nodes']:
        # These attr should not be set explicitly.
        for attr in ['data_dir_path', 'log_dir_path', 'innodb_log_dir_path']:
            if node.has_key(attr):
                raise ValueError('%s can not be set explicitly for meta node %s:%d' % (attr, node['ip'], node['port']))
        addPortToMachine(portmap, node['ip'], node['port'])
        if node.has_key('xport'):
            addPortToMachine(portmap, node['ip'], node['xport'])
        if node.has_key('mgr_port'):
            addPortToMachine(portmap, node['ip'], node['mgr_port'])
        if node.get('is_primary', False):
            if hasPrimary:
                raise ValueError('Error: Two primaries found in meta shard, there should be one and only one Primary specified !')
            else:
                hasPrimary = True
    if nodecnt > 1:
        if not hasPrimary:
            raise ValueError('Error: No primary found in meta shard, there should be one and only one !')
    elif nodecnt > 0:
            node['is_primary'] = True

    clustermgrips = set()
    for node in clustermgr['nodes']:
        if node['ip'] in clustermgrips:
            raise ValueError('Error: %s exists, only one cluster_mgr can be run on a machine!' % node['ip'])
        clustermgrips.add(node['ip'])
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
    nodemgrips = set()
    for node in nodemgr['nodes']:
        mach = machines.get(node['ip'])
        if node['ip'] in nodemgrips:
            raise ValueError('Error: %s exists, only one node_mgr can be run on a machine!' % node['ip'])
        nodemgrips.add(node['ip'])
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
                dirs = set()
                for d in nodedirs.split(","):
                    formald = d.strip()
                    #addDirToMachine(dirmap, node['ip'], d)
                    if not formald.startswith('/'):
                        raise ValueError('Error: the dir in %s must be absolute path!' % item)
                    if formald in dirs:
                        raise ValueError('Error: duplicate dir on %s(%s): %s!' % (node['ip'], item, d))
                    dirs.add(formald)
            else:
                node[item] = "%s/%s" % (mach['basedir'], defpaths[item])

def get_ha_mode(jscfg, args):
    meta = jscfg['meta']
    if len(meta['nodes']) > 1:
        return cluster.get('ha_mode', 'mgr')
    else:
        return 'no_rep'

def get_default_nodemgr(args, machines, ip):
    mach = machines.get(ip)
    defpaths = {
            "server_datadirs": "server_datadir",
            "storage_datadirs": "storage_datadir",
            "storage_logdirs": "storage_logdir",
            "storage_waldirs": "storage_waldir",
        }
    node =  {
            'ip': ip,
            'brpc_http_port': args.defbrpc_http_port_nodemgr
            }
    for item in ["server_datadirs", "storage_datadirs", "storage_logdirs", "storage_waldirs"]:
        node[item] = "%s/%s" % (mach['basedir'], defpaths[item])
    return node

def install_meta_env(comf, node, machines, args):
    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    ip = node['ip']
    mach = machines.get(ip)
    # Set up the files
    process_command_setenv(comf, args, machines, ip, '.', 'mkdir -p %s' %  node['program_dir'])
    process_file(comf, args, machines, ip, 'clustermgr/%s.tgz' % storagedir, '%s/%s' % (mach['basedir'], node['program_dir']))
    process_file(comf, args, machines, ip, 'clustermgr/%s.tgz' % serverdir, '%s/%s' % (mach['basedir'], node['program_dir']))
    process_command_setenv(comf, args, machines, ip, node['program_dir'], 'tar -xzf %s.tgz' % storagedir)
    process_command_setenv(comf, args, machines, ip, node['program_dir'], 'tar -xzf %s.tgz' % serverdir)
    comstr = "bash %s/process_deps.sh"
    process_command_setenv(comf, args, machines, ip,
        "%s/%s/lib" % (node['program_dir'], storagedir), comstr % mach['basedir'], "storage")
    process_command_setenv(comf, args, machines, ip,
        "%s/%s/lib" % (node['program_dir'], serverdir), comstr % mach['basedir'], "computing")
    comstr = "test -d etc && echo > etc/instances_list.txt 2>/dev/null; exit 0"
    process_command_setenv(comf, args, machines, ip, "%s/%s" % (node['program_dir'], storagedir), comstr)

def install_nodemgr_env(comf, mach, machines, args):
    progname = "kunlun-node-manager-%s" % args.product_version
    ip = mach['ip']
    # Set up the files
    process_file(comf, args, machines, ip, 'clustermgr/%s.tgz' % progname, mach['basedir'])
    process_command_noenv(comf, args, machines, ip, mach['basedir'], 'tar -xzf %s.tgz' % progname)

def setup_nodemgr_commands(args, idx, machines, node, commandslist, dirmap, filesmap, metaseeds):
    cmdpat = "bash change_config.sh %s '%s' '%s'\n"
    nodemgrdir = "kunlun-node-manager-%s" % args.product_version
    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    confpath = "%s/conf/node_mgr.cnf" % nodemgrdir
    mach = machines.get(node['ip'])
    targetdir = "program_binaries"
    setup_mgr_common(commandslist, dirmap, filesmap, machines, node, targetdir, storagedir, serverdir)
    for item in ["server_datadirs", "storage_datadirs", "storage_logdirs", "storage_waldirs"]:
        nodedirs = node[item].strip()
        for d in nodedirs.split(","):
            addToDirMap(dirmap, node['ip'], d.strip())
    addNodeToFilesMap(filesmap, node, "hadoop-3.3.1.tar.gz", targetdir)
    addNodeToFilesMap(filesmap, node, "jdk-8u131-linux-x64.tar.gz", targetdir)
    addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf hadoop-3.3.1.tar.gz")
    addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf jdk-8u131-linux-x64.tar.gz")
    addToCommandsList(commandslist, node['ip'], nodemgrdir, "chmod a+x bin/util/*")
    script_name = "setup_nodemgr_%d.sh" % idx
    scriptf = open('clustermgr/%s' % script_name, 'w')
    scriptf.write("#! /bin/bash\n")
    scriptf.write(cmdpat % (confpath, 'meta_group_seeds', metaseeds))
    scriptf.write(cmdpat % (confpath, 'brpc_http_port', node['brpc_http_port']))
    scriptf.write(cmdpat % (confpath, 'local_ip', node['ip']))
    scriptf.write(cmdpat % (confpath, 'program_binaries_path', '%s/program_binaries' % mach['basedir']))
    scriptf.write(cmdpat % (confpath, 'instance_binaries_path', '%s/instance_binaries' % mach['basedir']))
    scriptf.write(cmdpat % (confpath, 'prometheus_path', '%s/program_binaries/prometheus' % mach['basedir']))
    scriptf.write(cmdpat % (confpath, 'storage_prog_package_name', storagedir))
    scriptf.write(cmdpat % (confpath, 'computer_prog_package_name', serverdir))
    scriptf.close()
    addNodeToFilesMap(filesmap, node, script_name, '.')
    addNodeToFilesMap(filesmap, node, 'clear_instances.sh', '.')
    addToCommandsList(commandslist, node['ip'], '.', "bash ./%s" % script_name)

def install_clustermgr_env(comf, mach, machines, args):
    progname = "kunlun-cluster-manager-%s" % args.product_version
    ip = mach['ip']
    # Set up the files
    process_file(comf, args, machines, ip, 'clustermgr/%s.tgz' % progname, mach['basedir'])
    process_command_noenv(comf, args, machines, ip, mach['basedir'], 'tar -xzf %s.tgz' % progname)

def setup_clustermgr_commands(args, idx, machines, node, commandslist, dirmap, filesmap, metaseeds, initmember, initcommon):
    cmdpat = "bash change_config.sh %s '%s' '%s'\n"
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version
    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    confpath = "%s/conf/cluster_mgr.cnf" % clustermgrdir
    mach = machines.get(node['ip'])
    targetdir = "program_binaries"
    if initcommon:
        setup_mgr_common(commandslist, dirmap, filesmap, machines, node, targetdir, storagedir, serverdir)
    script_name = "setup_clustermgr_%d.sh" % idx
    scriptf = open('clustermgr/%s' % script_name, 'w')
    scriptf.write("#! /bin/bash\n")
    scriptf.write(cmdpat % (confpath, 'meta_group_seeds', metaseeds))
    scriptf.write(cmdpat % (confpath, 'brpc_raft_port', node['brpc_raft_port']))
    scriptf.write(cmdpat % (confpath, 'brpc_http_port', node['brpc_http_port']))
    scriptf.write(cmdpat % (confpath, 'local_ip', node['ip']))
    scriptf.write(cmdpat % (confpath, 'raft_group_member_init_config', initmember))
    scriptf.write(cmdpat % (confpath, 'program_binaries_path', '%s/program_binaries' % mach['basedir']))
    scriptf.write(cmdpat % (confpath, 'instance_binaries_path', '%s/instance_binaries' % mach['basedir']))
    scriptf.write(cmdpat % (confpath, 'prometheus_path', '%s/program_binaries/prometheus' % mach['basedir']))
    scriptf.write(cmdpat % (confpath, 'storage_prog_package_name', storagedir))
    scriptf.write(cmdpat % (confpath, 'computer_prog_package_name', serverdir))
    scriptf.close()
    addNodeToFilesMap(filesmap, node, script_name, '.')
    addToCommandsList(commandslist, node['ip'], '.', "bash ./%s" % script_name)

def setup_machines(jscfg, machines, args):
    machnodes = jscfg.get('machines', [])
    meta = jscfg['meta']
    metanodes = meta.get('nodes', [])
    nodemgr = jscfg.get('node_manager', {"nodes": []})
    nodemgrnodes = nodemgr.get('nodes', [])
    clustermgr = jscfg.get('cluster_manager', {"nodes": []})
    clustermgrnodes = clustermgr.get('nodes', [])
    for mach in machnodes:
	ip=mach['ip']
	user=mach.get('user', args.defuser)
	base=mach.get('basedir', args.defbase)
	addMachineToMap(machines, ip, user, base)
    for node in metanodes:
        addIpToMachineMap(machines, node['ip'], args)
    for node in nodemgrnodes:
        addIpToMachineMap(machines, node['ip'], args)
    for node in clustermgrnodes:
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

def setup_mgr_common(commandslist, dirmap, filesmap, machines, node, targetdir, storagedir, serverdir):
    mach = machines.get(node['ip'])
    addToDirMap(dirmap, node['ip'], "%s/%s" % (mach['basedir'], targetdir))
    addToDirMap(dirmap, node['ip'], "%s/%s/util" % (mach['basedir'], targetdir))
    addToDirMap(dirmap, node['ip'], "%s/instance_binaries" % mach['basedir'])
    addNodeToFilesMap(filesmap, node, "prometheus.tgz", targetdir)
    addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf prometheus.tgz")
    addNodeToFilesMap(filesmap, node, "%s.tgz" % storagedir, targetdir)
    addNodeToFilesMap(filesmap, node, "%s.tgz" % serverdir, targetdir)
    addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf %s.tgz" % storagedir)
    addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf %s.tgz" % serverdir)
    addToCommandsList(commandslist, node['ip'], "%s/%s/lib" %(targetdir, storagedir), "bash %s/process_deps.sh" % mach['basedir'])
    addToCommandsList(commandslist, node['ip'], "%s/%s/lib" %(targetdir, serverdir), "bash %s/process_deps.sh" % mach['basedir'])
    #addToCommandsList(commandslist, node['ip'], targetdir, "rm -f %s.tgz" % storagedir)
    #addToCommandsList(commandslist, node['ip'], targetdir, "tar -czf %s.tgz %s" % (storagedir, storagedir))
    #addToCommandsList(commandslist, node['ip'], targetdir, "rm -f %s.tgz" % serverdir)
    #addToCommandsList(commandslist, node['ip'], targetdir, "tar -czf %s.tgz %s" % (serverdir, serverdir))

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
    meta_addrs = []
    metaips = set()
    for node in meta['nodes']:
        metaips.add(node['ip'])
        meta_addrs.append("%s:%s" % (node['ip'], str(node['port'])))
    metaseeds = meta.get('group_seeds', '')
    if metaseeds == '':
        metaseeds=",".join(meta_addrs)
        print 'metaseeds:%s' % metaseeds

    nodemgrips = set()
    nodemgrmaps = {}
    for node in nodemgr['nodes']:
        nodemgrips.add(node['ip'])
        nodemgrmaps[node['ip']] = node
    for ip in metaips:
        if ip not in nodemgrips:
            node = get_default_nodemgr(args, machines, ip)
            nodemgr['nodes'].append(node)
            nodemgrmaps[ip] = node
            nodemgrips.add(ip)
    for node in meta['nodes']:
        set_metapath_using_nodemgr(machines, node, nodemgrmaps.get(node['ip']))

    clustermgrips = set()
    members=[]
    for node in clustermgr['nodes']:
        clustermgrips.add(node['ip'])
        members.append("%s:%d:0" % (node['ip'], node['brpc_raft_port']))
    initmember = clustermgr.get('raft_group_member_init_config', '')
    if initmember == '':
        initmember = "%s," % ",".join(members)

    # used for install storage nodes
    my_metaname = 'mysql_meta.json'
    reg_metaname = 'reg_meta.json'
    if not meta.has_key('group_uuid'):
	    meta['group_uuid'] = getuuid()
    if len(meta['nodes']) > 0:
        metaf = open(r'clustermgr/%s' % my_metaname,'w')
        json.dump(meta, metaf, indent=4)
        metaf.close()
        metaf = open(r'clustermgr/%s' % reg_metaname, 'w')
        objs = []
        for node in meta['nodes']:
	    mach = machines.get(node['ip'])
	    obj = {}
	    obj['is_primary'] = node.get('is_primary', False)
            obj['data_dir_path'] = node['data_dir_path']
	    obj['nodemgr_bin_path'] = "%s/%s/bin" % (mach['basedir'], nodemgrdir)
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
    shard_id = 'meta'
    pries = []
    secs = []
    i = 0
    for node in meta['nodes']:
	targetdir='%s/%s/dba_tools' % (node['program_dir'], storagedir)
	addNodeToFilesMap(filesmap, node, reg_metaname, "%s/%s/scripts" % (node['program_dir'], serverdir))
	addNodeToFilesMap(filesmap, node, my_metaname, targetdir)
	cmd = cmdpat % (sudopfx, my_metaname, i, cluster_name, shard_id)
	if node.get('is_primary', False):
            pries.append([node['ip'], targetdir, cmd])
	else:
            secs.append([node['ip'], targetdir, cmd])
	addToDirMap(dirmap, node['ip'], node['data_dir_path'])
	addToDirMap(dirmap, node['ip'], node['log_dir_path'])
	addToDirMap(dirmap, node['ip'], node['innodb_log_dir_path'])
        if args.autostart:
            generate_storage_service(args, machines, commandslist, node, i, filesmap)
	i+=1
    for item in pries:
        addToCommandsList(commandslist, item[0], item[1], item[2] + extraopt)
    for item in secs:
        addToCommandsList(commandslist, item[0], item[1], item[2] + extraopt)

    # bootstrap the cluster
    if len(meta['nodes']) > 0:
        firstmeta = meta['nodes'][0]
        targetdir='%s/%s/scripts' % (firstmeta['program_dir'], serverdir)
        cmdpat=r'python2 bootstrap.py --config=./%s --bootstrap_sql=./meta_inuse.sql' + extraopt
        addToCommandsList(commandslist, firstmeta['ip'], targetdir, cmdpat % reg_metaname, "storage")

    if len(nodemgr['nodes']) > 0:
        nodemgrjson = "nodemgr.json"
        nodemgrf = open('clustermgr/%s' % nodemgrjson, 'w')
        json.dump(nodemgr['nodes'], nodemgrf, indent=4)
        nodemgrf.close()
        worknode = None
        if len(meta['nodes']) > 0:
            worknode = meta['nodes'][0]
        elif len(nodemgr['nodes']) > 0:
            worknode = nodemgr['nodes'][0]
        else:
            worknode = clustermgr['nodes'][0]
        if worknode is not None:
            ip = worknode['ip']
            mach = machines.get(ip)
            addNodeToFilesMap(filesmap, worknode, 'modify_servernodes.py', '.')
            addNodeToFilesMap(filesmap, worknode, nodemgrjson, '.')
            addToCommandsList(commandslist, ip, machines.get(worknode['ip'])['basedir'],
                "python2 modify_servernodes.py --config %s --action=add --seeds=%s" % (nodemgrjson, metaseeds))
    i = 0
    for node in nodemgr['nodes']:
        setup_nodemgr_commands(args, i, machines, node, commandslist, dirmap, filesmap, metaseeds)
        if args.autostart:
            generate_nodemgr_service(args, machines, commandslist, node, i, filesmap)
        i += 1

    i = 0
    for node in clustermgr['nodes']:
        setup_clustermgr_commands(args, i, machines, node, commandslist, dirmap, filesmap, metaseeds, initmember, ip not in nodemgrips)
        if args.autostart:
            generate_clustermgr_service(args, machines, commandslist, node, i, filesmap)
        i += 1

    # start the nodemgr and clustermgr process finally.
    for node in nodemgr['nodes']:
        addToCommandsList(commandslist, node['ip'], "%s/bin" % nodemgrdir, "bash start_node_mgr.sh </dev/null >& run.log &")
    for node in clustermgr['nodes']:
        addToCommandsList(commandslist, node['ip'], "%s/bin" % clustermgrdir, "bash start_cluster_mgr.sh </dev/null >& start.log &")

    workips = set()
    workips.update(metaips)
    workips.update(nodemgrips)
    workips.update(clustermgrips)
    print "workips:%s" % str(workips)
    for ip in workips:
	mach = machines.get(ip)
	if args.sudo:
            process_command_noenv(comf, args, machines, ip, '/',
                'sudo mkdir -p %s && sudo chown -R %s:\`id -gn %s\` %s' % (mach['basedir'],
                    mach['user'], mach['user'], mach['basedir']))
	else:
            process_command_noenv(comf, args, machines, ip, '/', 'mkdir -p %s' % mach['basedir'])
        process_file(comf, args, machines, ip, 'env.sh.template', mach['basedir'])
        extstr = "sed -s 's#KUNLUN_BASEDIR#%s#g' env.sh.template > env.sh" % mach['basedir']
        process_command_noenv(comf, args, machines, ip, mach['basedir'], extstr)
        extstr = "sed -i 's#KUNLUN_VERSION#%s#g' env.sh" % args.product_version
        process_command_noenv(comf, args, machines, ip, mach['basedir'], extstr)
        process_file(comf, args, machines, ip, 'install/process_deps.sh', mach['basedir'])
        process_file(comf, args, machines, ip, 'install/change_config.sh', mach['basedir'])
        process_file(comf, args, machines, ip, 'install/build_driver_formysql.sh', mach['basedir'])
        process_file(comf, args, machines, ip, 'clustermgr/mysql-connector-python-2.1.3.tar.gz', mach['basedir'])
        process_command_noenv(comf, args, machines, ip, mach['basedir'], 'bash ./build_driver_formysql.sh %s' % mach['basedir'])

   # setup env for meta
    for node in meta['nodes']:
        install_meta_env(comf, node, machines, args)

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
	for fpair in fmap:
            process_file(comf, args, machines, ip, 'clustermgr/%s' % fpair[0], '%s/%s' % (mach['basedir'], fpair[1]))

    # The reason for not using commands map is that, we need to keep the order for the commands.
    process_commandslist_setenv(comf, args, machines, commandslist)

def generate_systemctl_clean(servname, ip, commandslist):
    syscmdpat1 = "sudo systemctl stop %s"
    syscmdpat2 = "sudo systemctl disable %s"
    syscmdpat3 = "sudo rm -f /usr/lib/systemd/system/%s"
    addToCommandsList(commandslist, ip, '/', syscmdpat1 % servname)
    addToCommandsList(commandslist, ip, '/', syscmdpat2 % servname)
    addToCommandsList(commandslist, ip, '/', syscmdpat3 % servname)

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

    metaips = set()
    meta_addrs = []
    for node in meta['nodes']:
        metaips.add(node['ip'])
        meta_addrs.append("%s:%s" % (node['ip'], str(node['port'])))
    metaseeds = meta.get('group_seeds', '')
    if metaseeds == '':
        metaseeds=",".join(meta_addrs)

    nodemgrips = set()
    nodemgrmaps = {}
    for node in nodemgr['nodes']:
        nodemgrips.add(node['ip'])
        nodemgrmaps[node['ip']] = node
    for ip in metaips:
        if ip not in nodemgrips:
            node = get_default_nodemgr(args, machines, ip)
            nodemgr['nodes'].append(node)
            nodemgrmaps[ip] = node
            nodemgrips.add(ip)
    for node in meta['nodes']:
        set_metapath_using_nodemgr(machines, node, nodemgrmaps.get(node['ip']))

    clustermgrips = set()
    for node in clustermgr['nodes']:
        clustermgrips.add(node['ip'])

    # clean the meta nodes
    for node in meta['nodes']:
        targetdir='%s/%s/dba_tools' % (node['program_dir'], storagedir)
	cmdpat = r'bash stopmysql.sh %d'
	addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'], "storage")
	cmdpat = r'%srm -fr %s'
	addToCommandsList(commandslist, node['ip'], ".", cmdpat % (sudopfx, node['log_dir_path']))
	addToCommandsList(commandslist, node['ip'], ".", cmdpat % (sudopfx, node['data_dir_path']))
	addToCommandsList(commandslist, node['ip'], ".", cmdpat % (sudopfx, node['innodb_log_dir_path']))
        addToCommandsList(commandslist, node['ip'], ".", cmdpat % (sudopfx, node['program_dir']))
        if args.autostart:
            servname = 'kunlun-storage-%d.service' % node['port']
            generate_systemctl_clean(servname, node['ip'], commandslist)

    # stop the nodemgr processes
    for node in nodemgr['nodes']:
        mach = machines.get(node['ip'])
        addToCommandsList(commandslist, node['ip'], "%s/bin" % nodemgrdir, "bash stop_node_mgr.sh")
        #for item in ["server_datadirs", "storage_datadirs", "storage_logdirs", "storage_waldirs"]:
        #    nodedirs = node[item].strip()
        #    for d in nodedirs.split(","):
        #        cmdpat = '%srm -fr %s/*'
        #        addToCommandsList(commandslist, node['ip'], "/", cmdpat % (sudopfx, d))
        addNodeToFilesMap(filesmap, node, 'clear_instances.sh', '.')
        addToCommandsList(commandslist, node['ip'], ".", 'bash ./clear_instances.sh %s %s >& clear.log || true' % (mach['basedir'], args.product_version))
        addToCommandsList(commandslist, node['ip'], "", '%srm -fr %s/%s' % (sudopfx, mach['basedir'], nodemgrdir))
        if args.autostart:
            servname = 'kunlun-node-manager-%d.service' % node['brpc_http_port']
            generate_systemctl_clean(servname, node['ip'], commandslist)


    # stop the nodemgr processes
    for node in clustermgr['nodes']:
        addToCommandsList(commandslist, node['ip'], "%s/bin" % clustermgrdir, "bash stop_cluster_mgr.sh")
        addToCommandsList(commandslist, node['ip'], "", '%srm -fr %s/%s' % (sudopfx, mach['basedir'], clustermgrdir))
        if args.autostart:
            servname = 'kunlun-cluster-manager-%d.service' % node['brpc_raft_port']
            generate_systemctl_clean(servname, node['ip'], commandslist)

    if len(nodemgr['nodes']) > 0 and meta.has_key('group_seeds'):
        nodemgrjson = "nodemgr.json"
        nodemgrf = open('clustermgr/%s' % nodemgrjson, 'w')
        json.dump(nodemgr['nodes'], nodemgrf, indent=4)
        nodemgrf.close()
        worknode = None
        if len(meta['nodes']) > 0:
            worknode = meta['nodes'][0]
        elif len(nodemgr['nodes']) > 0:
            worknode = nodemgr['nodes'][0]
        else:
            worknode = clustermgr['nodes'][0]
        if worknode is not None:
            ip = worknode['ip']
            mach = machines.get(ip)
            addNodeToFilesMap(filesmap, worknode, 'modify_servernodes.py', '.')
            addNodeToFilesMap(filesmap, worknode, nodemgrjson, '.')
            addToCommandsList(commandslist, ip, machines.get(worknode['ip'])['basedir'],
                "python2 modify_servernodes.py --config %s --action=remove --seeds=%s" % (nodemgrjson, metaseeds))

    # files copy.
    for ip in filesmap:
	mach = machines.get(ip)
	fmap = filesmap[ip]
	for fpair in fmap:
            process_file(comf, args, machines, ip, 'clustermgr/%s' % fpair[0], '%s/%s' % (mach['basedir'], fpair[1]))

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
    parser.add_argument('--defuser', type=str, help="the default user", default=getpass.getuser())
    parser.add_argument('--defbase', type=str, help="the default basedir", default='/kunlun')
    parser.add_argument('--sudo', help="whether to use sudo", default=False, action='store_true')
    parser.add_argument('--product_version', type=str, help="kunlun version", default='0.9.2')
    parser.add_argument('--localip', type=str, help="The local ip address", default='127.0.0.1')
    parser.add_argument('--small', help="whether to use small template", default=False, action='store_true')
    parser.add_argument('--autostart', help="whether to start the cluster automaticlly", default=False, action='store_true')
    parser.add_argument('--defbrpc_raft_port_clustermgr', type=int, help="default brpc_raft_port for cluster_manager", default=58001)
    parser.add_argument('--defbrpc_http_port_clustermgr', type=int, help="default brpc_http_port for cluster_manager", default=58000)
    parser.add_argument('--defbrpc_http_port_nodemgr', type=int, help="default brpc_http_port for node_manager", default=58002)

    args = parser.parse_args()
    if not args.defbase.startswith('/'):
        raise ValueError('Error: the default basedir must be absolute path!')
    if args.autostart:
        args.sudo = True

    print str(sys.argv)
    checkdirs(['clustermgr'])
    if args.action == 'install':
        install_clustermgr(args)
    elif args.action == 'clean':
        clean_clustermgr(args)
    else:
        # just defensive, for more more actions later.
        pass
