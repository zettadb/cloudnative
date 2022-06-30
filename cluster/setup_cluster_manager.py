#!/bin/python2
# Copyright (c) 2019 ZettaDB inc. All rights reserved.
# This source code is licensed under Apache 2.0 License,
# combined with Common Clause Condition 1.0, as detailed in the NOTICE file.

import sys
import json
import getpass
import argparse
from cluster_common import *

def generate_server_startstop(args, machines, node, idx, filesmap):
    mach = machines.get(node['ip'])
    serverdir = "kunlun-server-%s" % args.product_version
    envfname = 'env.sh.nodemgr'
    # start wrapper
    startname = '%d-start-server-%d.sh' % (idx, node['port'])
    startname_to = 'start-server-%d.sh' % node['port']
    startf = open('clustermgr/%s' % startname, 'w')
    startf.write("#! /bin/bash\n")
    startf.write("cd %s || exit 1\n" % mach['basedir'])
    startf.write("test -f %s && . ./%s\n" % (envfname, envfname))
    startf.write("cd instance_binaries/computer/%s/%s/scripts || exit 1\n" % (str(node['port']), serverdir))
    startf.write("python2 start_pg.py --port=%d\n" % node['port'])
    startf.close()
    addNodeToFilesListMap(filesmap, node, startname, './%s' % startname_to)
    # stop wrapper, actually may not be necessary.
    stopname = '%d-stop-server-%d.sh' % (idx, node['port'])
    stopname_to = 'stop-server-%d.sh' % node['port']
    stopf = open('clustermgr/%s' % stopname, 'w')
    stopf.write("#! /bin/bash\n")
    stopf.write("cd %s || exit 1\n" % mach['basedir'])
    stopf.write("test -f %s && . ./%s\n" % (envfname, envfname))
    stopf.write("cd instance_binaries/computer/%s/%s/scripts || exit 1\n" % (str(node['port']), serverdir))
    stopf.write("python2 stop_pg.py --port=%d\n" % node['port'])
    stopf.close()
    addNodeToFilesListMap(filesmap, node, stopname, './%s' % stopname_to)

def generate_storage_startstop(args, machines, node, idx, filesmap):
    mach = machines.get(node['ip'])
    storagedir = "kunlun-storage-%s" % args.product_version
    envfname = 'env.sh.nodemgr'
    # start wrapper
    startname = '%d-start-storage-%d.sh' % (idx, node['port'])
    startname_to = 'start-storage-%d.sh' % node['port']
    startf = open('clustermgr/%s' % startname, 'w')
    startf.write("#! /bin/bash\n")
    startf.write("cd %s || exit 1\n" % mach['basedir'])
    startf.write("test -f %s && . ./%s\n" % (envfname, envfname))
    startf.write("cd instance_binaries/storage/%s/%s/dba_tools || exit 1\n" % (str(node['port']), storagedir))
    startf.write("bash startmysql.sh %d\n" % node['port'])
    startf.close()
    addNodeToFilesListMap(filesmap, node, startname, './%s' % startname_to)
    # stop wrapper, actually may not be necessary.
    stopname = '%d-stop-storage-%d.sh' % (idx, node['port'])
    stopname_to = 'stop-storage-%d.sh' % node['port']
    stopf = open('clustermgr/%s' % stopname, 'w')
    stopf.write("#! /bin/bash\n")
    stopf.write("cd %s || exit 1\n" % mach['basedir'])
    stopf.write("test -f %s && . ./%s\n" % (envfname, envfname))
    stopf.write("cd instance_binaries/storage/%s/%s/dba_tools || exit 1\n" % (str(node['port']), storagedir))
    stopf.write("bash stopmysql.sh %d\n" % node['port'])
    stopf.close()
    addNodeToFilesListMap(filesmap, node, stopname, './%s' % stopname_to)

def generate_storage_service(args, machines, commandslist, node, idx, filesmap):
    mach = machines.get(node['ip'])
    nodemgrobj = node['nodemgr']
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
    servicef.write("WorkingDirectory=%s\n" % (mach['basedir']))
    servicef.write("ExecStart=/bin/bash start-storage-%d.sh\n" % (node['port']))
    servicef.write("ExecStop=/bin/bash stop-storage-%d.sh\n" % (node['port']))
    servicef.close()
    addNodeToFilesListMap(filesmap, node, fname, './%s' % fname_to)
    addToCommandsList(commandslist, node['ip'], '.', "sudo cp -f %s /usr/lib/systemd/system/" % fname_to)
    addToCommandsList(commandslist, node['ip'], '.', "sudo systemctl enable %s" % servname)

def generate_clustermgr_startstop(args, machines, node, idx, filesmap):
    mach = machines.get(node['ip'])
    clsutermgrdir = "kunlun-clustermgr-manager-%s" % args.product_version
    # start wrapper
    startname = '%d-start-clustermgr-%d.sh' % (idx, node['brpc_raft_port'])
    startname_to = 'start-clustermgr-%d.sh' % node['brpc_raft_port']
    startf = open('clustermgr/%s' % startname, 'w')
    startf.write("#! /bin/bash\n")
    startf.write("cd %s || exit 1\n" % mach['basedir'])
    startf.write("cd %s/bin || exit 1\n" % clsutermgrdir)
    startf.write("bash start_cluster_mgr.sh\n")
    startf.close()
    addNodeToFilesListMap(filesmap, node, startname, './%s' % startname_to)
    addNodeToFilesListMap(filesmap, node, startname, './start-clustermgr.sh')
    # stop wrapper, actually may not be necessary.
    stopname = '%d-stop-clustermgr-%d.sh' % (idx, node['brpc_raft_port'])
    stopname_to = 'stop-clustermgr-%d.sh' % node['brpc_raft_port']
    stopf = open('clustermgr/%s' % stopname, 'w')
    stopf.write("#! /bin/bash\n")
    stopf.write("cd %s || exit 1\n" % mach['basedir'])
    stopf.write("cd %s/bin || exit 1\n" % clsutermgrdir)
    stopf.write("bash stop_cluster_mgr.sh\n")
    stopf.close()
    addNodeToFilesListMap(filesmap, node, stopname, './%s' % stopname_to)
    addNodeToFilesListMap(filesmap, node, stopname, './stop-clustermgr.sh')

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
    addNodeToFilesListMap(filesmap, node, fname, './%s' % fname_to)
    addToCommandsList(commandslist, node['ip'], '.', "sudo cp -f %s /usr/lib/systemd/system/" % fname_to)
    addToCommandsList(commandslist, node['ip'], '.', "sudo systemctl enable %s" % servname)

def generate_nodemgr_startstop(args, machines, node, idx, filesmap):
    mach = machines.get(node['ip'])
    nodemgrdir = "kunlun-node-manager-%s" % args.product_version
    envfname = 'env.sh.nodemgr'
    # start wrapper
    startname = '%d-start-nodemgr-%d.sh' % (idx, node['brpc_http_port'])
    startname_to = 'start-nodemgr-%d.sh' % node['brpc_http_port']
    startf = open('clustermgr/%s' % startname, 'w')
    startf.write("#! /bin/bash\n")
    startf.write("cd %s || exit 1\n" % mach['basedir'])
    startf.write("test -f %s && . ./%s\n" % (envfname, envfname))
    startf.write("cd %s/bin || exit 1\n" % nodemgrdir)
    startf.write("bash start_node_mgr.sh\n")
    startf.close()
    addNodeToFilesListMap(filesmap, node, startname, './%s' % startname_to)
    addNodeToFilesListMap(filesmap, node, startname, './start-nodemgr.sh')
    # stop wrapper, actually may not be necessary.
    stopname = '%d-stop-nodemgr-%d.sh' % (idx, node['brpc_http_port'])
    stopname_to = 'stop-nodemgr-%d.sh' % node['brpc_http_port']
    stopf = open('clustermgr/%s' % stopname, 'w')
    stopf.write("#! /bin/bash\n")
    stopf.write("cd %s || exit 1\n" % mach['basedir'])
    stopf.write("test -f %s && . ./%s\n" % (envfname, envfname))
    stopf.write("cd %s/bin || exit 1\n" % nodemgrdir)
    stopf.write("bash stop_node_mgr.sh\n")
    stopf.close()
    addNodeToFilesListMap(filesmap, node, stopname, './%s' % stopname_to)
    addNodeToFilesListMap(filesmap, node, stopname, './stop-nodemgr.sh')

def generate_nodemgr_service(args, machines, commandslist, node, idx, filesmap):
    mach = machines.get(node['ip'])
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
    servicef.write("WorkingDirectory=%s\n" % mach['basedir'])
    servicef.write("ExecStart=/bin/bash start-nodemgr-%d.sh\n" % node['brpc_http_port'])
    servicef.write("ExecStop=/bin/bash stop-nodemgr-%d.sh\n" % node['brpc_http_port'])
    servicef.close()
    addNodeToFilesListMap(filesmap, node, fname, './%s' % fname_to)
    addToCommandsList(commandslist, node['ip'], '.', "sudo cp -f %s /usr/lib/systemd/system/" % fname_to)
    addToCommandsList(commandslist, node['ip'], '.', "sudo systemctl enable %s" % servname)

def generate_nodemgr_env(args, machines, node, idx, filesmap):
    mach = machines.get(node['ip'])
    jdk = "jdk1.8.0_131"
    hadoop = "hadoop-3.3.1"
    fname = '%d-env.sh.%d' % (idx, node['brpc_http_port'])
    fname_to = 'env.sh.nodemgr'
    envf = open('clustermgr/%s' % fname, 'w')
    envf.write("#! /bin/bash\n")
    envf.write("JAVA_HOME=%s/program_binaries/%s\n" % (mach['basedir'], jdk))
    envf.write("PATH=$JAVA_HOME/bin:$PATH\n")
    envf.write("HADOOP_HOME=%s/program_binaries/%s\n" % (mach['basedir'], hadoop))
    envf.write("PATH=$HADOOP_HOME/bin:$PATH\n")
    envf.write("export JAVA_HOME\n")
    envf.write("export HADOOP_HOME\n")
    envf.write("export PATH\n")
    envf.close()
    addNodeToFilesListMap(filesmap, node, fname, './%s' % fname_to)

def setup_meta_env(node, machines, dirmap, commandslist, args):
    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    mach = machines.get(node['ip'])
    # Set up the files
    addToDirMap(dirmap, node['ip'], "%s/%s" % (mach['basedir'], node['program_dir']))
    addToCommandsList(commandslist, node['ip'], '.', 'cp -fr %s/program_binaries/%s %s' %  (mach['basedir'], storagedir, node['program_dir']))
    addToCommandsList(commandslist, node['ip'], '.', 'cp -fr %s/program_binaries/%s %s' %  (mach['basedir'], serverdir, node['program_dir']))

def setup_storage_env(node, machines, dirmap, commandslist, args):
    storagedir = "kunlun-storage-%s" % args.product_version
    mach = machines.get(node['ip'])
    # Set up the files
    addToDirMap(dirmap, node['ip'], "%s/%s" % (mach['basedir'], node['program_dir']))
    addToCommandsList(commandslist, node['ip'], '.', 'cp -fr %s/program_binaries/%s %s' %  (mach['basedir'], storagedir, node['program_dir']))

def setup_server_env(node, machines, dirmap, commandslist, args):
    serverdir = "kunlun-server-%s" % args.product_version
    mach = machines.get(node['ip'])
    # Set up the files
    addToDirMap(dirmap, node['ip'], "%s/%s" % (mach['basedir'], node['program_dir']))
    addToCommandsList(commandslist, node['ip'], '.', 'cp -fr %s/program_binaries/%s %s' %  (mach['basedir'], serverdir, node['program_dir']))

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
    addNodeToFilesListMap(filesmap, node, "%s.tgz" % storagedir, targetdir)
    addNodeToFilesListMap(filesmap, node, "%s.tgz" % serverdir, targetdir)
    addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf %s.tgz" % storagedir)
    addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf %s.tgz" % serverdir)
    addToCommandsList(commandslist, node['ip'], targetdir, "rm -f %s.tgz" % storagedir)
    addToCommandsList(commandslist, node['ip'], targetdir, "rm -f %s.tgz" % serverdir)
    addToCommandsList(commandslist, node['ip'], "%s/%s/lib" %(targetdir, storagedir), "bash %s/process_deps.sh" % mach['basedir'])
    addToCommandsList(commandslist, node['ip'], "%s/%s/lib" %(targetdir, serverdir), "bash %s/process_deps.sh" % mach['basedir'])
    comstr = "test -d etc && echo > etc/instances_list.txt 2>/dev/null; exit 0"
    addToCommandsList(commandslist, node['ip'], "%s/%s" %(targetdir, storagedir), comstr)
    addToCommandsList(commandslist, node['ip'], "%s/%s" %(targetdir, serverdir), comstr)
    setup_mgr_common(commandslist, dirmap, filesmap, machines, node, targetdir, storagedir, serverdir)
    for item in ["server_datadirs", "storage_datadirs", "storage_logdirs", "storage_waldirs"]:
        nodedirs = node[item].strip()
        for d in nodedirs.split(","):
            addToDirMap(dirmap, node['ip'], d.strip())
    addNodeToFilesListMap(filesmap, node, "hadoop-3.3.1.tar.gz", targetdir)
    addNodeToFilesListMap(filesmap, node, "jdk-8u131-linux-x64.tar.gz", targetdir)
    addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf hadoop-3.3.1.tar.gz")
    addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf jdk-8u131-linux-x64.tar.gz")
    addToCommandsList(commandslist, node['ip'], nodemgrdir, "chmod a+x bin/util/*")
    script_name = "setup_nodemgr_%d.sh" % idx
    scriptf = open('clustermgr/%s' % script_name, 'w')
    scriptf.write("#! /bin/bash\n")
    scriptf.write(cmdpat % (confpath, 'meta_group_seeds', metaseeds))
    scriptf.write(cmdpat % (confpath, 'brpc_http_port', node['brpc_http_port']))
    scriptf.write(cmdpat % (confpath, 'nodemgr_tcp_port', node['tcp_port']))
    scriptf.write(cmdpat % (confpath, 'local_ip', node['ip']))
    scriptf.write(cmdpat % (confpath, 'program_binaries_path', '%s/program_binaries' % mach['basedir']))
    scriptf.write(cmdpat % (confpath, 'instance_binaries_path', '%s/instance_binaries' % mach['basedir']))
    scriptf.write(cmdpat % (confpath, 'prometheus_path', '%s/program_binaries/prometheus' % mach['basedir']))
    scriptf.write(cmdpat % (confpath, 'storage_prog_package_name', storagedir))
    scriptf.write(cmdpat % (confpath, 'computer_prog_package_name', serverdir))
    scriptf.close()
    addNodeToFilesListMap(filesmap, node, script_name, '.')
    addNodeToFilesListMap(filesmap, node, 'clear_instances.sh', '.')
    addNodeToFilesListMap(filesmap, node, 'clear_instance.sh', '.')
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
    scriptf.write(cmdpat % (confpath, 'prometheus_path', '%s/program_binaries/prometheus' % mach['basedir']))
    scriptf.close()
    addNodeToFilesListMap(filesmap, node, script_name, '.')
    addToCommandsList(commandslist, node['ip'], '.', "bash ./%s" % script_name)

def install_clustermgr(args):
    jscfg = get_json_from_file(args.config)
    machines = {}
    setup_machines2(jscfg, machines, args)
    validate_and_set_config2(jscfg, machines, args)
    comf = open(r'clustermgr/install.sh', 'w')
    comf.write('#! /bin/bash\n')
    install_with_config(jscfg, comf, machines, args)
    comf.close()

def stop_clustermgr(args):
    jscfg = get_json_from_file(args.config)
    machines = {}
    setup_machines2(jscfg, machines, args)
    validate_and_set_config2(jscfg, machines, args)
    comf = open(r'clustermgr/stop.sh', 'w')
    comf.write('#! /bin/bash\n')
    stop_with_config(jscfg, comf, machines, args)
    comf.close()

def start_clustermgr(args):
    jscfg = get_json_from_file(args.config)
    machines = {}
    setup_machines2(jscfg, machines, args)
    validate_and_set_config2(jscfg, machines, args)
    comf = open(r'clustermgr/start.sh', 'w')
    comf.write('#! /bin/bash\n')
    start_with_config(jscfg, comf, machines, args)
    comf.close()

def clean_clustermgr(args):
    jscfg = get_json_from_file(args.config)
    machines = {}
    setup_machines2(jscfg, machines, args)
    validate_and_set_config2(jscfg, machines, args)
    comf = open(r'clustermgr/clean.sh', 'w')
    comf.write('#! /bin/bash\n')
    clean_with_config(jscfg, comf, machines, args)
    comf.close()

def setup_mgr_common(commandslist, dirmap, filesmap, machines, node, targetdir, storagedir, serverdir):
    mach = machines.get(node['ip'])
    addToDirMap(dirmap, node['ip'], "%s/%s" % (mach['basedir'], targetdir))
    addToDirMap(dirmap, node['ip'], "%s/%s/util" % (mach['basedir'], targetdir))
    addToDirMap(dirmap, node['ip'], "%s/instance_binaries" % mach['basedir'])
    addNodeToFilesListMap(filesmap, node, "prometheus.tgz", targetdir)
    addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf prometheus.tgz")
    #addToCommandsList(commandslist, node['ip'], targetdir, "rm -f %s.tgz" % storagedir)
    #addToCommandsList(commandslist, node['ip'], targetdir, "tar -czf %s.tgz %s" % (storagedir, storagedir))
    #addToCommandsList(commandslist, node['ip'], targetdir, "rm -f %s.tgz" % serverdir)
    #addToCommandsList(commandslist, node['ip'], targetdir, "tar -czf %s.tgz %s" % (serverdir, serverdir))

def install_clusters(jscfg, machines, dirmap, filesmap, commandslist, reg_metaname, args):
    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    clusters = jscfg['clusters']
    meta_hamode = jscfg['meta']['ha_mode']
    
    i = 1
    for cluster in clusters:
        cluster_name = cluster['name']
        
        # Storage nodes
        cmdpat = '%spython2 install-mysql.py --config=./%s --target_node_index=%d --cluster_id=%s --shard_id=%s --server_id=%d'
        if cluster['storage_template'] == 'small':
            cmdpat += ' --dbcfg=./template-small.cnf'
        extraopt = " --ha_mode=%s" % cluster['ha_mode']
        j = 1
        pries = []
        secs = []
        for shard in cluster['data']:
            if not 'group_uuid' in shard:
                shard['group_uuid'] = getuuid()
            shard_id = "shard%d" % i
            my_shardname = "cluster%d_shard%d.json" % (i,j)
            shardf = open(r'clustermgr/%s' % my_shardname, 'w')
            json.dump(shard, shardf, indent=4)
            shardf.close()
            k = 0
            for node in shard['nodes']:
                targetdir='%s/%s/dba_tools' % (node['program_dir'], storagedir)
                addNodeToFilesListMap(filesmap, node, my_shardname, targetdir)
                mach = machines.get(node['ip'])
                absenvfname = '%s/env.sh.nodemgr' % (mach['basedir'])
                envpfx = "test -f %s && . %s; " % (absenvfname, absenvfname)
                cmd = cmdpat % (envpfx, my_shardname, k, cluster_name, shard_id, k+1)
                generate_storage_startstop(args, machines, node, k, filesmap)
                if node.get('is_primary', False):
                    pries.append([node['ip'], targetdir, cmd])
                else:
                    secs.append([node['ip'], targetdir, cmd])
                addToDirMap(dirmap, node['ip'], node['data_dir_path'])
                addToDirMap(dirmap, node['ip'], node['log_dir_path'])
                addToDirMap(dirmap, node['ip'], node['innodb_log_dir_path'])
                k += 1
            j += 1
        for item in pries:
            addToCommandsList(commandslist, item[0], item[1], item[2] + extraopt)
        for item in secs:
            addToCommandsList(commandslist, item[0], item[1], item[2] + extraopt)

        # Computing nodes
        pg_compname = 'cluster%d_comp.json' % i
        compf = open(r'clustermgr/%s' % pg_compname, 'w')
        json.dump([], compf, indent=4)
        compf.close()
        reg_shardname = "cluster%d_shards.json" % i
        shardf = open(r'clustermgr/%s' % reg_shardname, 'w')
        shards = []
        j = 1
        for shard in cluster['data']:
            obj = {'shard_name': 'shard%d' % j}
            j += 1
            nodes = []
            for node in shard['nodes']:
                n = {'user':'pgx', 'password':'pgx_pwd'}
                n['ip'] = node['ip']
                n['port'] = node['port']
                nodes.append(n)
            obj['shard_nodes'] = nodes
            shards.append(obj)
        json.dump(shards, shardf, indent=4)
        shardf.close()

        node = cluster['comp']['nodes'][0]
        targetdir='%s/%s/scripts' % (node['program_dir'], serverdir)
        addNodeToFilesListMap(filesmap, node, pg_compname, targetdir)
        addNodeToFilesListMap(filesmap, node, reg_metaname, targetdir)
        addNodeToFilesListMap(filesmap, node, reg_shardname, targetdir)
        cmdpat='python2 create_cluster.py --shards_config=./%s \
--comps_config=./%s  --meta_config=./%s --cluster_name=%s --meta_ha_mode=%s --ha_mode=%s --cluster_owner=abc --cluster_biz=test'
        addToCommandsList(commandslist, node['ip'], targetdir,
            cmdpat % (reg_shardname, pg_compname, reg_metaname, cluster_name, meta_hamode, cluster['ha_mode']), "all")

        cmdpat = r'%spython2 add_comp_self.py  --meta_config=./%s --cluster_name=%s --user=%s --password=%s --port=%d --mysql_port=%d --datadir=%s --install --ha_mode=%s'
        idx=0
        for node in cluster['comp']['nodes']:
            targetdir='%s/%s/scripts' % (node['program_dir'], serverdir)
            addNodeToFilesListMap(filesmap, node, reg_metaname, targetdir)
            mach = machines.get(node['ip'])
            absenvfname = '%s/env.sh.nodemgr' % (mach['basedir'])
            envpfx = "test -f %s && . %s; " % (absenvfname, absenvfname)
            addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (envpfx, reg_metaname, cluster_name,
                node['user'], node['password'], node['port'], node['mysql_port'], node['datadir'], meta_hamode))
            addToDirMap(dirmap, node['ip'], node['datadir'])
            generate_server_startstop(args, machines, node, idx, filesmap)
            idx += 1
        i += 1

def start_clusters(clusters, nodemgrmaps, machines, comf):
    commandslist = []
    targetdir = '.'
    for cluster in clusters:
        cmdpat = "bash start-storage-%d.sh"
        for shard in cluster['data']:
            for node in shard['nodes']:
                nodemgrobj = nodemgrmaps.get(node['ip'])
                if not nodemgrobj['skip']:
                    continue
                addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'])
        cmdpat = "bash start-server-%d.sh"
        for node in cluster['comp']['nodes']:
            nodemgrobj = nodemgrmaps.get(node['ip'])
            if not nodemgrobj['skip']:
                continue
            addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'])
    process_commandslist_setenv(comf, args, machines, commandslist)

def stop_clusters(clusters, nodemgrmaps, machines, comf):
    commandslist = []
    targetdir = '.'
    for cluster in clusters:
        cmdpat = "bash stop-storage-%d.sh"
        for shard in cluster['data']:
            for node in shard['nodes']:
                nodemgrobj = nodemgrmaps.get(node['ip'])
                if not nodemgrobj['skip']:
                    continue
                addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'])
        cmdpat = "bash stop-server-%d.sh"
        for node in cluster['comp']['nodes']:
            nodemgrobj = nodemgrmaps.get(node['ip'])
            if not nodemgrobj['skip']:
                continue
            addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'])
    process_commandslist_setenv(comf, args, machines, commandslist)

def clean_clusters(args, clusters, nodemgrmaps, machines, comf):
    commandslist = []
    targetdir = '.'
    for cluster in clusters:
        cmdpat = "bash clear_instance.sh %d storage %s %s"
        for shard in cluster['data']:
            for node in shard['nodes']:
                nodemgrobj = nodemgrmaps.get(node['ip'])
                if not nodemgrobj['skip']:
                    continue
                mach = machines.get(node['ip'])
                addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (node['port'], mach['basedir'], args.product_version))
        cmdpat = "bash clear_instance.sh %d server %s %s"
        for node in cluster['comp']['nodes']:
            nodemgrobj = nodemgrmaps.get(node['ip'])
            if not nodemgrobj['skip']:
                continue
            mach = machines.get(node['ip'])
            addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (node['port'], mach['basedir'], args.product_version))
    process_commandslist_setenv(comf, args, machines, commandslist)

def install_with_config(jscfg, comf, machines, args):
    meta = jscfg['meta']
    clustermgr = jscfg['cluster_manager']
    nodemgr = jscfg['node_manager']
    ha_mode = meta.get('ha_mode', '')
    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version
    nodemgrdir = "kunlun-node-manager-%s" % args.product_version

    filesmap = {}
    commandslist = []
    dirmap = {}

    cluster_name = 'meta'
    extraopt = " --ha_mode=%s" % ha_mode
    meta_addrs = []
    for node in meta['nodes']:
        meta_addrs.append("%s:%s" % (node['ip'], str(node['port'])))
    metaseeds = meta.get('group_seeds', '')
    if metaseeds == '':
        metaseeds=",".join(meta_addrs)
        my_print('metaseeds:%s' % metaseeds)

    nodemgrmaps = {}
    for node in nodemgr['nodes']:
        nodemgrmaps[node['ip']] = node

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
    xpanel_sqlfile = 'dba_tools_db.sql'
    if not 'group_uuid' in meta:
	    meta['group_uuid'] = getuuid()
    metaf = open(r'clustermgr/%s' % reg_metaname, 'w')
    objs = []
    if len(meta['nodes']) > 0:
        tempf = open(r'clustermgr/%s' % my_metaname,'w')
        json.dump(meta, tempf, indent=4)
        tempf.close()
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
    elif not metaseeds == '': # For case just providing the seeds.
        for addr in metaseeds.split(','):
            parts = addr.split(':')
            obj = {}
            obj['is_primary'] = False
            obj['data_dir_path'] = ''
            obj['nodemgr_bin_path'] = ''
            obj['ip'] = parts[0]
            if (len(parts) > 1):
                obj['port'] = int(parts[1])
            else:
                obj['port'] = 3306
            obj['user'] = "pgx"
            obj['password'] = "pgx_pwd"
            objs.append(obj)
    json.dump(objs, metaf, indent=4)
    metaf.close()

    i = 0
    nodemgrips = set()
    for node in nodemgr['nodes']:
        nodemgrips.add(node['ip'])
        if node['skip']:
            continue
        setup_nodemgr_commands(args, i, machines, node, commandslist, dirmap, filesmap, metaseeds)
        generate_nodemgr_env(args, machines, node, i, filesmap)
        generate_nodemgr_startstop(args, machines, node, i, filesmap)
        if args.autostart:
            generate_nodemgr_service(args, machines, commandslist, node, i, filesmap)
        i += 1

   # setup env for meta
    for node in meta['nodes']:
        setup_meta_env(node, machines, dirmap, commandslist, args)

    # setup for init clusters
    for cluster in jscfg['clusters']:
        for shard in cluster['data']:
            for node in shard['nodes']:
                setup_storage_env(node, machines, dirmap, commandslist, args)
        for node in cluster['comp']['nodes']:
            setup_server_env(node, machines, dirmap, commandslist, args)

    prefilesmap = filesmap
    filesmap = {}
    precommandslist = commandslist
    commandslist = []
    cmdpat = '%spython2 install-mysql.py --config=./%s --target_node_index=%d --cluster_id=%s --shard_id=%s --server_id=%d'
    if args.small:
        cmdpat += ' --dbcfg=./template-small.cnf'
    # commands like:
    # python2 install-mysql.py --config=./mysql_meta.json --target_node_index=0 --server_id=[int]
    shard_id = 'meta'
    pries = []
    secs = []
    i = 0
    for node in meta['nodes']:
        targetdir='%s/%s/dba_tools' % (node['program_dir'], storagedir)
        node['nodemgr'] = nodemgrmaps.get(node['ip'])
        mach = machines.get(node['ip'])
        absenvfname = '%s/env.sh.%d' % (mach['basedir'], node['nodemgr']['brpc_http_port'])
        envpfx = "test -f %s && . %s; " % (absenvfname, absenvfname)
        addNodeToFilesListMap(filesmap, node, reg_metaname, "%s/%s/scripts" % (node['program_dir'], serverdir))
        addNodeToFilesListMap(filesmap, node, my_metaname, targetdir)
        addNodeToFilesListMap(filesmap, node, xpanel_sqlfile, targetdir)
        cmd = cmdpat % (envpfx, my_metaname, i, cluster_name, shard_id, i+1)
        if node.get('is_primary', False):
            pries.append([node['ip'], targetdir, cmd])
        else:
            secs.append([node['ip'], targetdir, cmd])
        addToDirMap(dirmap, node['ip'], node['data_dir_path'])
        addToDirMap(dirmap, node['ip'], node['log_dir_path'])
        addToDirMap(dirmap, node['ip'], node['innodb_log_dir_path'])
        generate_storage_startstop(args, machines, node, i, filesmap)
        generate_storage_service(args, machines, commandslist, node, i, filesmap)
        i+=1
    for item in pries:
        addToCommandsList(commandslist, item[0], item[1], item[2] + extraopt)
    for item in secs:
        addToCommandsList(commandslist, item[0], item[1], item[2] + extraopt)

    # bootstrap the cluster
    if len(meta['nodes']) > 0:
        #firstmeta = meta['nodes'][0]
        firstmeta = None
        for node in meta['nodes']:
            if node.get('is_primary', False):
                firstmeta = node
                break
        targetdir='%s/%s/scripts' % (firstmeta['program_dir'], serverdir)
        cmdpat=r'python2 bootstrap.py --config=./%s --bootstrap_sql=./meta_inuse.sql' + extraopt
        addToCommandsList(commandslist, firstmeta['ip'], targetdir, cmdpat % reg_metaname, "computing")
        cmdpat=r'bash imysql.sh %s < %s'
        targetdir='%s/%s/dba_tools' % (firstmeta['program_dir'], storagedir)
        addToCommandsList(commandslist, firstmeta['ip'], targetdir, cmdpat % (str(firstmeta['port']), xpanel_sqlfile), "storage")

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
            addNodeToFilesListMap(filesmap, worknode, 'modify_servernodes.py', '.')
            addNodeToFilesListMap(filesmap, worknode, nodemgrjson, '.')
            addToCommandsList(commandslist, ip, machines.get(worknode['ip'])['basedir'],
                "python2 modify_servernodes.py --config %s --action=add --seeds=%s" % (nodemgrjson, metaseeds))

    install_clusters(jscfg, machines, dirmap, filesmap, commandslist, reg_metaname, args)

    i = 0
    for node in clustermgr['nodes']:
        setup_clustermgr_commands(args, i, machines, node, commandslist, dirmap, filesmap, metaseeds, initmember, ip not in nodemgrips)
        if args.autostart:
            generate_clustermgr_service(args, machines, commandslist, node, i, filesmap)
        i += 1

    # start the nodemgr and clustermgr process finally.
    for node in nodemgr['nodes']:
        addToCommandsList(commandslist, node['ip'], ".", "bash start-nodemgr-%d.sh </dev/null >& run.log &" % node['brpc_http_port'])
    for node in clustermgr['nodes']:
        addToCommandsList(commandslist, node['ip'], "%s/bin" % clustermgrdir, "bash start_cluster_mgr.sh </dev/null >& start.log &")

    workips = set()
    workips.update(nodemgrips)
    workips.update(clustermgrips)
    my_print("workips:%s" % str(workips))
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

   # setup env for nodemgr
    for ip in nodemgrips:
        nodemgrobj = nodemgrmaps.get(ip)
        if nodemgrobj['skip']:
            continue
        mach = machines.get(ip)
        install_nodemgr_env(comf, mach, machines, args)

   # setup env for nodemgr
    for ip in clustermgrips:
        mach = machines.get(ip)
        install_clustermgr_env(comf, mach, machines, args)

    process_dirmap(comf, dirmap, machines, args)
    process_fileslistmap(comf, prefilesmap, machines, 'clustermgr', args)
    process_commandslist_setenv(comf, args, machines, precommandslist)
    process_fileslistmap(comf, filesmap, machines, 'clustermgr', args)
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

    meta_addrs = []
    for node in meta['nodes']:
        meta_addrs.append("%s:%s" % (node['ip'], str(node['port'])))
    metaseeds = meta.get('group_seeds', '')
    if metaseeds == '':
        metaseeds=",".join(meta_addrs)

    nodemgrmaps = {}
    for node in nodemgr['nodes']:
        nodemgrmaps[node['ip']] = node

    # clean the nodemgr processes
    for node in nodemgr['nodes']:
        if node['skip']:
            continue
        mach = machines.get(node['ip'])
        addToCommandsList(commandslist, node['ip'], "%s/bin" % nodemgrdir, "bash stop_node_mgr.sh")
        #for item in ["server_datadirs", "storage_datadirs", "storage_logdirs", "storage_waldirs"]:
        #    nodedirs = node[item].strip()
        #    for d in nodedirs.split(","):
        #        cmdpat = '%srm -fr %s/*'
        #        addToCommandsList(commandslist, node['ip'], "/", cmdpat % (sudopfx, d))
        addNodeToFilesListMap(filesmap, node, 'clear_instances.sh', '.')
        addToCommandsList(commandslist, node['ip'], ".", 'bash ./clear_instances.sh %s %s >& clear.log || true' % (
            mach['basedir'], args.product_version))
        addToCommandsList(commandslist, node['ip'], "", '%srm -fr %s/%s' % (sudopfx, mach['basedir'], nodemgrdir))
        if args.autostart:
            servname = 'kunlun-node-manager-%d.service' % node['brpc_http_port']
            generate_systemctl_clean(servname, node['ip'], commandslist)

    clean_clusters(args, jscfg['clusters'], nodemgrmaps, machines, comf)

    # clean the nodemgr processes
    for node in clustermgr['nodes']:
        addToCommandsList(commandslist, node['ip'], "%s/bin" % clustermgrdir, "bash stop_cluster_mgr.sh")
        addToCommandsList(commandslist, node['ip'], "", '%srm -fr %s/%s' % (sudopfx, mach['basedir'], clustermgrdir))
        if args.autostart:
            servname = 'kunlun-cluster-manager-%d.service' % node['brpc_raft_port']
            generate_systemctl_clean(servname, node['ip'], commandslist)

    if len(nodemgr['nodes']) > 0 and 'group_seeds' in meta:
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
            addNodeToFilesListMap(filesmap, worknode, 'modify_servernodes.py', '.')
            addNodeToFilesListMap(filesmap, worknode, nodemgrjson, '.')
            addToCommandsList(commandslist, ip, machines.get(worknode['ip'])['basedir'],
                "python2 modify_servernodes.py --config %s --action=remove --seeds=%s" % (nodemgrjson, metaseeds))

    # clean the meta nodes
    for node in meta['nodes']:
        nodemgrobj = nodemgrmaps.get(node['ip'])
        # skip it if it is processed by nodemgr clean routine.
        if not nodemgrobj['skip']:
            continue
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

    process_fileslistmap(comf, filesmap, machines, 'clustermgr', args)
    process_commandslist_setenv(comf, args, machines, commandslist)

def generate_systemctl_stop(servname, ip, commandslist):
    syscmdpat1 = "sudo systemctl stop %s"
    addToCommandsList(commandslist, ip, '/', syscmdpat1 % servname)

def stop_with_config(jscfg, comf, machines, args):
    meta = jscfg['meta']
    clustermgr = jscfg['cluster_manager']
    nodemgr = jscfg['node_manager']
    storagedir = "kunlun-storage-%s" % args.product_version
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version
    nodemgrdir = "kunlun-node-manager-%s" % args.product_version

    filesmap = {}
    commandslist = []

    nodemgrmaps = {}
    for node in nodemgr['nodes']:
        nodemgrmaps[node['ip']] = node

    # stop the nodemgr processes
    for node in nodemgr['nodes']:
        if node['skip']:
            continue
        mach = machines.get(node['ip'])
        if args.autostart:
            servname = 'kunlun-node-manager-%d.service' % node['brpc_http_port']
            generate_systemctl_stop(servname, node['ip'], commandslist)
        else:
            addToCommandsList(commandslist, node['ip'], "%s/bin" % nodemgrdir, "bash stop_node_mgr.sh")
        addNodeToFilesListMap(filesmap, node, 'stop_instances.sh', '.')
        addToCommandsList(commandslist, node['ip'], ".", 'bash ./stop_instances.sh %s %s >& stop.log || true' % (
            mach['basedir'], args.product_version))

    stop_clusters(jscfg['clusters'], nodemgrmaps, machines, comf)

    # stop the clustermgr processes
    for node in clustermgr['nodes']:
        if args.autostart:
            servname = 'kunlun-cluster-manager-%d.service' % node['brpc_raft_port']
            generate_systemctl_stop(servname, node['ip'], commandslist)
        else:
            addToCommandsList(commandslist, node['ip'], "%s/bin" % clustermgrdir, "bash stop_cluster_mgr.sh")

    for node in meta['nodes']:
        nodemgrobj = nodemgrmaps.get(node['ip'])
        # skip it if it is processed by nodemgr clean routine.
        if not nodemgrobj['skip']:
            continue
        if args.autostart:
            servname = 'kunlun-storage-%d.service' % node['port']
            generate_systemctl_stop(servname, node['ip'], commandslist)
        else:
            targetdir='.'
            cmdpat = r'bash stop-storage-%d.sh'
            addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'], "storage")

    process_fileslistmap(comf, filesmap, machines, 'clustermgr', args)
    process_commandslist_setenv(comf, args, machines, commandslist)

def generate_systemctl_start(servname, ip, commandslist):
    syscmdpat1 = "sudo systemctl start %s"
    addToCommandsList(commandslist, ip, '/', syscmdpat1 % servname)

def start_with_config(jscfg, comf, machines, args):
    meta = jscfg['meta']
    clustermgr = jscfg['cluster_manager']
    nodemgr = jscfg['node_manager']
    storagedir = "kunlun-storage-%s" % args.product_version
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version
    nodemgrdir = "kunlun-node-manager-%s" % args.product_version

    filesmap = {}
    commandslist = []

    nodemgrmaps = {}
    for node in nodemgr['nodes']:
        nodemgrmaps[node['ip']] = node

    # start the nodemgr processes
    for node in nodemgr['nodes']:
        if node['skip']:
            continue
        if args.autostart:
            servname = 'kunlun-node-manager-%d.service' % node['brpc_http_port']
            generate_systemctl_start(servname, node['ip'], commandslist)
        else:
            mach = machines.get(node['ip'])
            addNodeToFilesListMap(filesmap, node, 'start_instances.sh', '.')
            addToCommandsList(commandslist, node['ip'], ".", 'bash ./start_instances.sh %s %s >& start.log || true' % (
                mach['basedir'], args.product_version))
            addToCommandsList(commandslist, node['ip'], '.', "bash start-nodemgr-%d.sh </dev/null >& run.log &" % node['brpc_http_port'])

    for node in meta['nodes']:
        nodemgrobj = nodemgrmaps.get(node['ip'])
        # skip it if it is processed by nodemgr clean routine.
        if not nodemgrobj['skip']:
            continue
        if args.autostart:
            servname = 'kunlun-storage-%d.service' % node['port']
            generate_systemctl_start(servname, node['ip'], commandslist)
        else:
            cmdpat = r'bash start-storage-%d.sh'
            addToCommandsList(commandslist, node['ip'], '.', cmdpat % node['port'], "storage")

    start_clusters(jscfg['clusters'], nodemgrmaps, machines, comf)

    # start the clustermgr processes
    for node in clustermgr['nodes']:
        if args.autostart:
            servname = 'kunlun-cluster-manager-%d.service' % node['brpc_raft_port']
            generate_systemctl_start(servname, node['ip'], commandslist)
        else:
            addToCommandsList(commandslist, node['ip'], "%s/bin" % clustermgrdir, "bash start_cluster_mgr.sh")

    process_fileslistmap(comf, filesmap, machines, 'clustermgr', args)
    process_commandslist_setenv(comf, args, machines, commandslist)

if  __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Specify the arguments.')
    actions=["install", "clean", "start", "stop"]
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
    parser.add_argument('--deftcp_port_nodemgr', type=int, help="default tcp_port for node_manager", default=58003)

    args = parser.parse_args()
    if not args.defbase.startswith('/'):
        raise ValueError('Error: the default basedir must be absolute path!')
    if args.autostart:
        args.sudo = True

    my_print(str(sys.argv))
    checkdirs(['clustermgr'])
    if args.action == 'install':
        install_clustermgr(args)
    elif args.action == 'clean':
        clean_clustermgr(args)
    elif args.action == 'start':
        start_clustermgr(args)
    elif args.action == 'stop':
        stop_clustermgr(args)
    else:
        # just defensive, for more more actions later.
        pass
