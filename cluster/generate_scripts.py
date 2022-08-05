#!/bin/python2
# Copyright (c) 2019 ZettaDB inc. All rights reserved.
# This source code is licensed under Apache 2.0 License,
# combined with Common Clause Condition 1.0, as detailed in the NOTICE file.

import sys
import json
import getpass
import argparse
from cluster_common import *

def generate_storage_service(args, machines, commandslist, node, idx, filesmap):
    mach = machines.get(node['ip'])
    storagedir = "kunlun-storage-%s" % args.product_version
    fname = "%d-kunlun-storage-%d.service" % (idx, node['port'])
    servname = "kunlun-storage-%d" % node['port']
    fname_to = "kunlun-storage-%d.service" % node['port']
    servicef = open('install/%s' % fname, 'w')
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
    servicef.write("WorkingDirectory=%s/%s/dba_tools\n" % (mach['basedir'], storagedir))
    servicef.write("ExecStart=/bin/bash startmysql.sh %d\n" % (node['port']))
    servicef.write("ExecStop=/bin/bash stopmysql.sh %d\n" % (node['port']))
    servicef.close()
    addNodeToFilesMap(filesmap, node, fname, './%s' % fname_to)
    addToCommandsList(commandslist, node['ip'], '.', "sudo cp -f %s /usr/lib/systemd/system/" % fname_to)
    addToCommandsList(commandslist, node['ip'], '.', "sudo systemctl enable %s" % servname)

def generate_server_service(args, machines, commandslist, node, idx, filesmap):
    mach = machines.get(node['ip'])
    serverdir = "kunlun-server-%s" % args.product_version
    fname = "%d-kunlun-server-%d.service" % (idx, node['port'])
    servname = "kunlun-server-%d" % node['port']
    fname_to = "kunlun-server-%d.service" % node['port']
    servicef = open('install/%s' % fname, 'w')
    servicef.write("# kunlun-server-%d systemd service file\n\n" % node['port'])
    servicef.write("[Unit]\n")
    servicef.write("Description=kunlun-server-%d\n" % node['port'])
    servicef.write("After=network.target\n\n")
    servicef.write("[Install]\n")
    servicef.write("WantedBy=multi-user.target\n\n")
    servicef.write("[Service]\n")
    servicef.write("Type=forking\n")
    servicef.write("User=%s\n" % mach['user'])
    servicef.write("Restart=on-failure\n")
    servicef.write("WorkingDirectory=%s/%s/scripts\n" % (mach['basedir'], serverdir))
    servicef.write("ExecStart=/usr/bin/python2 start_pg.py --port=%d\n" % (node['port']))
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
    servicef = open('install/%s' % fname, 'w')
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

def generate_haproxy_service(args, machines, commandslist, node, filesmap):
    mach = machines.get(node['ip'])
    fname = "kunlun-haproxy-%d.service" % (node['port'])
    servname = "kunlun-haproxy-%d" % node['port']
    servicef = open('install/%s' % fname, 'w')
    servicef.write("# Kunlun-HAProxy-%d systemd service file\n\n" % node['port'])
    servicef.write("[Unit]\n")
    servicef.write("Description=Kunlun-HAProxy-%d\n" % node['port'])
    servicef.write("After=network.target\n\n")
    servicef.write("[Install]\n")
    servicef.write("WantedBy=multi-user.target\n\n")
    servicef.write("[Service]\n")
    servicef.write("Type=forking\n")
    servicef.write("User=%s\n" % mach['user'])
    servicef.write("Restart=on-failure\n")
    servicef.write("WorkingDirectory=%s\n" % (mach['basedir'],))
    servicef.write("ExecStart=%s/haproxy-2.5.0-bin/sbin/haproxy -f haproxy.cfg\n" % (mach['basedir'],))
    servicef.close()
    addNodeToFilesMap(filesmap, node, fname, '.')
    addToCommandsList(commandslist, node['ip'], '.', "sudo cp -f %s /usr/lib/systemd/system/" % fname)
    addToCommandsList(commandslist, node['ip'], '.', "sudo systemctl enable %s" % servname)

def generate_install_scripts(jscfg, args):
    machines = {}
    setup_machines1(jscfg, machines, args)
    validate_and_set_config1(jscfg, machines, args)

    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version
    installtype = args.installtype

    valgrindopt = ""
    if args.valgrind:
        valgrindopt = "--valgrind"

    filesmap = {}
    commandslist = []
    dirmap = {}

    cluster = jscfg['cluster']
    cluster_name = cluster['name']
    meta = cluster['meta']
    datas = cluster['data']

    if not 'group_uuid' in meta:
	    meta['group_uuid'] = getuuid()
    meta_extraopt = " --ha_mode=%s" % meta['ha_mode']

    my_metaname = 'mysql_meta.json'
    metaf = open(r'install/%s' % my_metaname,'w')
    json.dump(meta, metaf, indent=4)
    metaf.close()

    cmdpat = 'python2 install-mysql.py --config=./%s --target_node_index=%d --cluster_id=%s --shard_id=%s --server_id=%d'
    if args.small:
        cmdpat += ' --dbcfg=./template-small.cnf'
    # commands like:
    # python2 install-mysql.py --config=./mysql_meta.json --target_node_index=0 --server_id=[int]
    targetdir='%s/dba_tools' % storagedir
    i=0
    storageidx = 0
    mpries = []
    msecs = []
    shard_id = "meta"
    meta_addrs = []
    for node in meta['nodes']:
        meta_addrs.append("%s:%s" % (node['ip'], str(node['port'])))
        addNodeToFilesMap(filesmap, node, my_metaname, targetdir)
        cmd = cmdpat % (my_metaname, i, cluster_name, shard_id, i+1)
        if node.get('is_primary', False):
            mpries.append([node['ip'], targetdir, cmd])
        else:
            msecs.append([node['ip'], targetdir, cmd])
        addToDirMap(dirmap, node['ip'], node['data_dir_path'])
        addToDirMap(dirmap, node['ip'], node['log_dir_path'])
        if 'innodb_log_dir_path' in node:
            addToDirMap(dirmap, node['ip'], node['innodb_log_dir_path'])
        if args.autostart:
            generate_storage_service(args, machines, commandslist, node, storageidx, filesmap)
        i+=1
        storageidx += 1

    pries = []
    secs = []
    shard_extraopt = " --ha_mode=%s" % cluster['ha_mode']
    i=1
    for shard in datas:
	    if not 'group_uuid' in shard:
                shard['group_uuid'] = getuuid()
	    shard_id = "shard%d" % i
	    my_shardname = "mysql_shard%d.json" % i
	    shardf = open(r'install/%s' % my_shardname, 'w')
	    json.dump(shard, shardf, indent=4)
	    shardf.close()
	    j = 0
	    for node in shard['nodes']:
                addNodeToFilesMap(filesmap, node, my_shardname, targetdir)
                cmd = cmdpat % (my_shardname, j, cluster_name, shard_id, j+1)
                if node.get('is_primary', False):
                    pries.append([node['ip'], targetdir, cmd])
                else:
                    secs.append([node['ip'], targetdir, cmd])
                addToDirMap(dirmap, node['ip'], node['data_dir_path'])
                addToDirMap(dirmap, node['ip'], node['log_dir_path'])
                if 'innodb_log_dir_path' in node:
                    addToDirMap(dirmap, node['ip'], node['innodb_log_dir_path'])
                if args.autostart:
                    generate_storage_service(args, machines, commandslist, node, storageidx, filesmap)
                j += 1
                storageidx += 1
	    i+=1

    for item in mpries:
        addToCommandsList(commandslist, item[0], item[1], item[2] + meta_extraopt)
    for item in pries:
        addToCommandsList(commandslist, item[0], item[1], item[2] + shard_extraopt)
    for item in msecs:
        addToCommandsList(commandslist, item[0], item[1], item[2] + meta_extraopt)
    for item in secs:
        addToCommandsList(commandslist, item[0], item[1], item[2] + shard_extraopt)

    comps = cluster['comp']['nodes']
    pg_compname = 'postgres_comp.json'
    compf = open(r'install/%s' % pg_compname, 'w')
    json.dump(comps, compf, indent=4)
    compf.close()

    # python2 install_pg.py --config=docker-comp.json --install_ids=1,2,3
    targetdir="%s/scripts" % serverdir
    for node in comps:
        addNodeToFilesMap(filesmap, node, pg_compname, targetdir)
        cmdpat = r'python2 install_pg.py  --config=./%s --install_ids=%d'
        addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (pg_compname, node['id']))
        addToDirMap(dirmap, node['ip'], node['datadir'])

    # This only needs to transfered to machine creating the cluster.
    reg_metaname = 'reg_meta.json'
    metaf = open(r'install/%s' % reg_metaname, 'w')
    objs = []
    for node in meta['nodes']:
        obj = {}
        obj['is_primary'] = node.get('is_primary', False)
        obj['data_dir_path'] = node['data_dir_path']
        obj['ip'] = node['ip']
        obj['port'] = node['port']
        obj['user'] = "pgx"
        obj['password'] = "pgx_pwd"
        if 'master_priority' in node:
            obj['master_priority'] = node['master_priority']
        objs.append(obj)
    json.dump(objs, metaf, indent=4)
    metaf.close()

    # This only needs to transfered to machine creating the cluster.
    reg_shardname = 'reg_shards.json'
    shardf = open(r'install/%s' % reg_shardname, 'w')
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
            if 'ro_weight' in node:
                n['ro_weight'] = node['ro_weight']
            if 'master_priority' in node:
                n['master_priority'] = node['master_priority']
            nodes.append(n)
        obj['shard_nodes'] = nodes
        shards.append(obj)
    json.dump(shards, shardf, indent=4)
    shardf.close()

    comp1 = comps[0]
    addNodeToFilesMap(filesmap, comp1, reg_metaname, targetdir)
    addNodeToFilesMap(filesmap, comp1, reg_shardname, targetdir)
    cmdpat=r'python2 bootstrap.py --config=./%s --bootstrap_sql=./meta_inuse.sql' + meta_extraopt
    addToCommandsList(commandslist, comp1['ip'], targetdir, cmdpat % reg_metaname, "storage")
    cmdpat='python2 create_cluster.py --shards_config=./%s \
--comps_config=./%s  --meta_config=./%s --cluster_name=%s --meta_ha_mode=%s --ha_mode=%s --cluster_owner=abc --cluster_biz=%s'
    addToCommandsList(commandslist, comp1['ip'], targetdir,
        cmdpat % (reg_shardname, pg_compname, reg_metaname, cluster_name, meta['ha_mode'], cluster['ha_mode'], cluster_name), "all")

    # bash -x bin/cluster_mgr_safe --debug --pidfile=run.pid clustermgr.cnf >& run.log </dev/null &
    clmgrnodes = jscfg['cluster']['clustermgr']['nodes']
    metaseeds=",".join(meta_addrs)
    clmgrcnf = "%s/conf/cluster_mgr.cnf" % clustermgrdir
    cmdpat = "bash change_config.sh %s '%s' '%s'"
    startpat = 'bash start_cluster_mgr.sh </dev/null >& start.log &'
    initmember = "%s:%d:0," % (clmgrnodes[0]['ip'], clmgrnodes[0]['brpc_raft_port'])
    clustermgridx = 0
    for node in clmgrnodes:
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (clmgrcnf, 'meta_group_seeds', metaseeds))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (clmgrcnf, 'brpc_raft_port', node['brpc_raft_port']))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (clmgrcnf, 'brpc_http_port', node['brpc_http_port']))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (clmgrcnf, 'local_ip', node['ip']))
        addToCommandsList(commandslist, node['ip'], '.', cmdpat % (clmgrcnf, 'raft_group_member_init_config', initmember))
        addToCommandsList(commandslist, node['ip'], "%s/bin" % clustermgrdir, startpat)
        if args.autostart:
            generate_clustermgr_service(args, machines, commandslist, node, clustermgridx, filesmap)
        clustermgridx += 1

    haproxy = cluster.get("haproxy", None)
    if haproxy is not None:
        generate_haproxy_config(jscfg['cluster'], machines, 'install', 'haproxy.cfg')
        cmdpat = r'haproxy-2.5.0-bin/sbin/haproxy -f haproxy.cfg >& haproxy.log'
        addToCommandsList(commandslist, haproxy['ip'], machines[haproxy['ip']]['basedir'], cmdpat)
        if args.autostart:
            generate_haproxy_service(args, machines, commandslist, haproxy, filesmap)

    initobj = cluster.get("initialization", None)
    initfile = "auto_init.sql"
    if initobj is not None:
        initsqlf = open("install/%s" % initfile, 'w')
        for sqlc in initobj.get("sqlcommands", []):
            initsqlf.write(sqlc)
            initsqlf.write(";\n")
        initsqlf.close()
        node = comps[0]
        waitTime = initobj.get("waitseconds", 10)
        addNodeToFilesMap(filesmap, node, initfile, ".")
        cmdpat = r'sleep %s; psql -f %s postgres://%s:%s@%s:%s/postgres'
        addToCommandsList(commandslist, node['ip'], ".",
            cmdpat % (str(waitTime), initfile, node['user'], node['password'], 'localhost', str(node['port'])), "computing")

    com_name = 'commands.sh'
    comf = open(r'install/%s' % com_name, 'w')
    comf.write('#! /bin/bash\n')

    # files copy.
    for ip in machines:
        mach = machines.get(ip)
        if args.sudo:
            process_command_noenv(comf, args, machines, ip, '/',
                'sudo mkdir -p %s && sudo chown -R %s:\`id -gn %s\` %s' % (mach['basedir'],
                    mach['user'], mach['user'], mach['basedir']))
        else:
            process_command_noenv(comf, args, machines, ip, '/', 'mkdir -p %s' % mach['basedir'])
	# Set up the files
        if installtype == 'full':
            process_file(comf, args, machines, ip, '%s.tgz' % storagedir, mach['basedir'])
            process_file(comf, args, machines, ip, '%s.tgz' % serverdir, mach['basedir'])
            process_file(comf, args, machines, ip, '%s.tgz' % clustermgrdir, mach['basedir'])
            process_command_noenv(comf, args, machines, ip, mach['basedir'], 'tar -xzf %s.tgz' % storagedir)
            process_command_noenv(comf, args, machines, ip, mach['basedir'], 'tar -xzf %s.tgz' % serverdir)
            process_command_noenv(comf, args, machines, ip, mach['basedir'], 'tar -xzf %s.tgz' % clustermgrdir)
            if 'haproxy' in cluster:
                process_file(comf, args, machines, ip, 'haproxy-2.5.0-bin.tar.gz', mach['basedir'])
                process_command_noenv(comf, args, machines, ip, mach['basedir'], 'tar -xzf haproxy-2.5.0-bin.tar.gz')

	# files
        flist = [
                    ['build_driver_forpg.sh', '%s/resources' % serverdir],
                    ['build_driver_formysql.sh', '%s/resources' % storagedir],
                    [reg_metaname, '%s/scripts' % serverdir],
                    ['process_deps.sh', '.'],
                    ['change_config.sh', '.']
                ]
        for fpair in flist:
            process_file(comf, args, machines, ip, 'install/%s' % fpair[0], "%s/%s" % (mach['basedir'], fpair[1]))
        if 'haproxy' in cluster:
            process_file(comf, args, machines, ip, 'install/haproxy.cfg', mach['basedir'])

	# Set up the env.sh, this must be before 'process_command_setenv'
        process_file(comf, args, machines, ip, 'install/env.sh.template', mach['basedir'])
        extstr = "sed -s 's#KUNLUN_BASEDIR#%s#g' env.sh.template > env.sh" % mach['basedir']
        process_command_noenv(comf, args, machines, ip, mach['basedir'], extstr)
        extstr = "sed -i 's#KUNLUN_VERSION#%s#g' env.sh" % args.product_version
        process_command_noenv(comf, args, machines, ip, mach['basedir'], extstr)

        comstr = "bash ../../process_deps.sh"
        process_command_setenv(comf, args, machines, ip, "%s/lib" % storagedir, comstr, "storage")
        process_command_setenv(comf, args, machines, ip, "%s/lib" % serverdir, comstr, "computing")

        comstr = "bash build_driver_formysql.sh %s"
        process_command_setenv(comf, args, machines, ip, "%s/resources" % storagedir, comstr % mach['basedir'], "storage")
        comstr = "bash build_driver_forpg.sh %s"
        process_command_setenv(comf, args, machines, ip, "%s/resources" % serverdir, comstr % mach['basedir'], "all")
 
        comstr = "cd %s || exit 1; test -d etc && echo > etc/instances_list.txt 2>/dev/null; exit 0" % serverdir
        process_command_noenv(comf, args, machines, ip, mach['basedir'], comstr)
        comstr = "cd %s || exit 1; test -d etc && echo > etc/instances_list.txt 2>/dev/null; exit 0" % storagedir
        process_command_noenv(comf, args, machines, ip, mach['basedir'], comstr)

    # dir making
    process_dirmap(comf, dirmap, machines, args)
    # files copy.
    process_filesmap(comf, filesmap, machines, 'install', args)
    # The reason for not using commands map is that, we need to keep the order for the commands.
    process_commandslist_setenv(comf, args, machines, commandslist)
    comf.close()

# The order is meta shard -> data shards -> cluster_mgr -> comp nodes
def generate_start_scripts(jscfg, args):
    machines = {}
    setup_machines1(jscfg, machines, args)
    validate_and_set_config1(jscfg, machines, args)

    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version

    valgrindopt = ""
    if args.valgrind:
        valgrindopt = "--valgrind"

    filesmap = {}
    commandslist = []
    
    cluster = jscfg['cluster']
    meta = cluster['meta']
    # commands like:
    # bash startmysql.sh [port]
    targetdir='%s/dba_tools' % storagedir
    for node in meta['nodes']:
        cmdpat = r'bash startmysql.sh %s'
        addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'])

    # bash startmysql.sh [port]
    targetdir='%s/dba_tools' % storagedir
    datas = cluster['data']
    for shard in datas:
	    for node in shard['nodes']:
                cmdpat = r'bash startmysql.sh %s'
                addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'])
    
    clmgrnodes = jscfg['cluster']['clustermgr']['nodes']
    cmdpat = r'bash start_cluster_mgr.sh </dev/null >& run.log &'
    for node in clmgrnodes:
        addToCommandsList(commandslist, node['ip'], "%s/bin" % clustermgrdir, cmdpat)

    # su postgres -c "python2 start_pg.py --port=5401"
    comps = cluster['comp']['nodes']
    targetdir="%s/scripts" % serverdir
    for node in comps:
        cmdpat = r'python2 start_pg.py --port=%d %s'
        addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (node['port'], valgrindopt), "computing")

    haproxy = cluster.get("haproxy", None)
    if haproxy is not None:
        cmdpat = r'haproxy-2.5.0-bin/sbin/haproxy -f haproxy.cfg >& haproxy.log'
        addToCommandsList(commandslist, haproxy['ip'], machines[haproxy['ip']]['basedir'], cmdpat)

    com_name = 'commands.sh'
    comf = open(r'start/%s' % com_name, 'w')
    comf.write('#! /bin/bash\n')
    process_commandslist_setenv(comf, args, machines, commandslist)
    comf.close()

# The order is: comp-nodes -> cluster_mgr -> data shards -> meta shard
def generate_stop_scripts(jscfg, args):
    machines = {}
    setup_machines1(jscfg, machines, args)
    validate_and_set_config1(jscfg, machines, args)

    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version

    commandslist = []
    cluster = jscfg['cluster']

    haproxy = cluster.get("haproxy", None)
    if haproxy is not None:
        cmdpat="cat haproxy.pid | xargs kill -9"
        addToCommandsList(commandslist, haproxy['ip'], machines[haproxy['ip']]['basedir'], cmdpat)

    # pg_ctl -D %s stop"
    comps = cluster['comp']['nodes']
    targetdir="%s/scripts" % serverdir
    for node in comps:
        cmdpat = r'pg_ctl -D %s stop -m immediate'
        addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['datadir'], "computing")

    clmgrnodes = jscfg['cluster']['clustermgr']['nodes']
    cmdpat = r'bash stop_cluster_mgr.sh'
    for node in clmgrnodes:
        addToCommandsList(commandslist, node['ip'], "%s/bin" % clustermgrdir, cmdpat)

    # bash stopmysql.sh [port]
    targetdir='%s/dba_tools' % storagedir
    datas = cluster['data']
    for shard in datas:
	    for node in shard['nodes']:
                cmdpat = r'bash stopmysql.sh %d'
                addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'], "storage")

    meta = cluster['meta']
    # commands like:
    # mysqladmin --defaults-file=/kunlun/kunlun-storage-$version/etc/my_6001.cnf -uroot -proot shutdown
    targetdir='%s/dba_tools' % storagedir
    for node in meta['nodes']:
        cmdpat = r'bash stopmysql.sh %d'
        addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'], "storage")
    
    com_name = 'commands.sh'
    comf = open(r'stop/%s' % com_name, 'w')
    comf.write('#! /bin/bash\n')
    process_commandslist_setenv(comf, args, machines, commandslist)
    comf.close()

def generate_systemctl_clean(servname, ip, commandslist):
    syscmdpat1 = "sudo systemctl stop %s"
    syscmdpat2 = "sudo systemctl disable %s"
    syscmdpat3 = "sudo rm -f /usr/lib/systemd/system/%s"
    addToCommandsList(commandslist, ip, '/', syscmdpat1 % servname)
    addToCommandsList(commandslist, ip, '/', syscmdpat2 % servname)
    addToCommandsList(commandslist, ip, '/', syscmdpat3 % servname)

# The order is: comp-nodes -> cluster_mgr -> data shards -> meta shard
def generate_clean_scripts(jscfg, args):
    machines = {}
    setup_machines1(jscfg, machines, args)
    validate_and_set_config1(jscfg, machines, args)

    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version

    sudopfx=""
    if args.sudo:
        sudopfx="sudo "
    cleantype = args.cleantype

    env_cmdlist = []
    noenv_cmdlist = []
    cluster = jscfg['cluster']

    haproxy = cluster.get("haproxy", None)
    if haproxy is not None:
        cmdpat="cat haproxy.pid | xargs kill -9"
        addToCommandsList(noenv_cmdlist, haproxy['ip'], machines[haproxy['ip']]['basedir'], cmdpat)
        cmdpat="rm -f haproxy.pid"
        addToCommandsList(noenv_cmdlist, haproxy['ip'], machines[haproxy['ip']]['basedir'], cmdpat)
        if args.autostart:
            servname = 'kunlun-haproxy-%d.service' % haproxy['port']
            generate_systemctl_clean(servname, haproxy['ip'], noenv_cmdlist)

    # pg_ctl -D %s stop"
    comps = cluster['comp']['nodes']
    targetdir="%s/scripts" % serverdir
    for node in comps:
        cmdpat = r'pg_ctl -D %s stop -m immediate'
        addToCommandsList(env_cmdlist, node['ip'], targetdir, cmdpat % node['datadir'], "computing")
        cmdpat = r'%srm -fr %s'
        addToCommandsList(noenv_cmdlist, node['ip'], ".", cmdpat % (sudopfx, node['datadir']))
        if args.autostart:
            servname = 'kunlun-server-%d.service' % node['port']
            generate_systemctl_clean(servname, node['ip'], noenv_cmdlist)

    clmgrnodes = jscfg['cluster']['clustermgr']['nodes']
    cmdpat = r'bash stop_cluster_mgr.sh'
    for node in clmgrnodes:
        addToCommandsList(env_cmdlist, node['ip'], "%s/bin" % clustermgrdir, cmdpat)
        if args.autostart:
            servname = 'kunlun-cluster-manager-%d.service' % node['brpc_raft_port']
            generate_systemctl_clean(servname, node['ip'], noenv_cmdlist)

    # bash stopmysql.sh [port]
    targetdir='%s/dba_tools' % storagedir
    datas = cluster['data']
    for shard in datas:
	    for node in shard['nodes']:
                cmdpat = r'bash stopmysql.sh %d'
                addToCommandsList(env_cmdlist, node['ip'], targetdir, cmdpat % node['port'], "storage")
                cmdpat = r'%srm -fr %s'
                addToCommandsList(noenv_cmdlist, node['ip'], ".", cmdpat % (sudopfx, node['log_dir_path']))
                addToCommandsList(noenv_cmdlist, node['ip'], ".", cmdpat % (sudopfx, node['data_dir_path']))
                if 'innodb_log_dir_path' in node:
                    addToCommandsList(noenv_cmdlist, node['ip'], ".", cmdpat % (sudopfx, node['innodb_log_dir_path']))
                if args.autostart:
                    servname = 'kunlun-storage-%d.service' % node['port']
                    generate_systemctl_clean(servname, node['ip'], noenv_cmdlist)

    meta = cluster['meta']
    # commands like:
    # mysqladmin --defaults-file=/kunlun/kunlun-storage-$version/etc/my_6001.cnf -uroot -proot shutdown
    targetdir='%s/dba_tools' % storagedir
    for node in meta['nodes']:
        cmdpat = r'bash stopmysql.sh %d'
        addToCommandsList(env_cmdlist, node['ip'], targetdir, cmdpat % node['port'], "storage")
        cmdpat = r'%srm -fr %s'
        addToCommandsList(noenv_cmdlist, node['ip'], ".", cmdpat % (sudopfx, node['log_dir_path']))
        addToCommandsList(noenv_cmdlist, node['ip'], ".", cmdpat % (sudopfx, node['data_dir_path']))
        if 'innodb_log_dir_path' in node:
            addToCommandsList(noenv_cmdlist, node['ip'], ".", cmdpat % (sudopfx, node['innodb_log_dir_path']))
        if args.autostart:
            servname = 'kunlun-storage-%d.service' % node['port']
            generate_systemctl_clean(servname, node['ip'], noenv_cmdlist)

    if cleantype == 'full':
        for ip in machines:
            mach =machines[ip]
            cmdpat = '%srm -fr %s/*'
            addToCommandsList(noenv_cmdlist, ip, ".", cmdpat % (sudopfx, mach['basedir']))

    com_name = 'commands.sh'
    comf = open(r'clean/%s' % com_name, 'w')
    comf.write('#! /bin/bash\n')
    process_commandslist_setenv(comf, args, machines, env_cmdlist)
    process_commandslist_noenv(comf, args, machines, noenv_cmdlist)
    comf.close()

# The order is meta shard -> data shards -> cluster_mgr -> comp nodes
def generate_check_scripts(jscfg, args):
    machines = {}
    setup_machines1(jscfg, machines, args)
    validate_and_set_config1(jscfg, machines, args)


    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version

    filesmap = {}
    commandslist = []

    cluster = jscfg['cluster']
    meta = cluster['meta']
    metacnt = len(meta['nodes'])
    meta_hamode = cluster['meta']['ha_mode']
    cluster_hamode = cluster['ha_mode']

    # commands like:
    # bash check_storage.sh [host] [port] [ha_mode]
    targetdir='.'

    cmdpat = r'bash check_storage.sh %s %s %s'
    for node in meta['nodes']:
        addNodeToFilesMap(filesmap, node, 'check/check_storage.sh', targetdir)
        addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (node['ip'], str(node['port']), meta_hamode), "storage")

    datas = cluster['data']
    for shard in datas:
	    for node in shard['nodes']:
                addNodeToFilesMap(filesmap, node, 'check/check_storage.sh', targetdir)
                addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (node['ip'], str(node['port']), cluster_hamode), "storage")

    # commands like:
    # bash check_cluster_manager.sh [basedir]
    clmgrnodes = jscfg['cluster']['clustermgr']['nodes']
    cmdpat = r'bash check_cluster_manager.sh %s'
    for node in clmgrnodes:
        addNodeToFilesMap(filesmap, node, 'check/check_cluster_manager.sh', targetdir)
        mach = machines.get(node['ip'])
        addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (mach['basedir']), "clustermgr")

    # commands like
    # bash check_server.sh [port] [user] [password]
    comps = cluster['comp']['nodes']
    cmdpat=r'bash check_server.sh %s %s %s'
    for node in comps:
        addNodeToFilesMap(filesmap, node, 'check/check_server.sh', targetdir)
        addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (node['port'], node['user'], node['password']), "computing")

    com_name = 'commands.sh'
    comf = open(r'check/%s' % com_name, 'w')
    comf.write('#! /bin/bash\n')

    # files copy.
    process_filesmap(comf, filesmap, machines, '.', args)
    process_commandslist_setenv(comf, args, machines, commandslist)
    comf.close()

if  __name__ == '__main__':
    actions=["install", "start", "stop", "clean", "check"]
    parser = argparse.ArgumentParser(description='Specify the arguments.')
    parser.add_argument('--action', type=str, help="The action", required=True, choices=actions)
    parser.add_argument('--config', type=str, help="The cluster config path", required=True)
    parser.add_argument('--defuser', type=str, help="the default user", default=getpass.getuser())
    parser.add_argument('--defbase', type=str, help="the default basedir", default='/kunlun')
    parser.add_argument('--installtype', type=str, help="the install type", default='full', choices=['full', 'cluster'])
    parser.add_argument('--cleantype', type=str, help="the clean type", default='full', choices=['full', 'cluster'])
    parser.add_argument('--sudo', help="whether to use sudo", default=False, action='store_true')
    parser.add_argument('--autostart', help="whether to start the cluster automaticlly", default=False, action='store_true')
    parser.add_argument('--localip', type=str, help="The local ip address", default=gethostip())
    parser.add_argument('--product_version', type=str, help="kunlun version", default='1.0.1')
    parser.add_argument('--small', help="whether to use small template", default=False, action='store_true')
    parser.add_argument('--valgrind', help="whether to use valgrind", default=False, action='store_true')
    parser.add_argument('--defbrpc_raft_port', type=int, help="default brpc_raft_port for cluster_manager", default=58000)
    parser.add_argument('--defbrpc_http_port', type=int, help="default brpc_raft_port for cluster_manager", default=58001)

    args = parser.parse_args()
    if not args.defbase.startswith('/'):
        raise ValueError('Error: the default basedir must be absolute path!')
    checkdirs(actions)

    my_print(str(sys.argv))
    jscfg = get_json_from_file(args.config)
    if args.autostart:
        args.sudo = True

    if args.action == 'install':
        generate_install_scripts(jscfg, args)
    elif args.action == 'start':
        generate_start_scripts(jscfg, args)
    elif args.action == 'stop':
        generate_stop_scripts(jscfg, args)
    elif args.action == 'clean':
        generate_clean_scripts(jscfg, args)
    elif args.action == 'check':
        generate_check_scripts(jscfg, args)
    else:
        usage()
        sys.exit(1)
