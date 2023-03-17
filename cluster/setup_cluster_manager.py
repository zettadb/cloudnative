#!/bin/python2
# Copyright (c) 2019 ZettaDB inc. All rights reserved.
# This source code is licensed under Apache 2.0 License,
# combined with Common Clause Condition 1.0, as detailed in the NOTICE file.

import sys
import json
import getpass
import argparse
import platform
from cluster_common import *

def purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist):
    process_dirmap(comf, dirmap, machines, args)
    process_fileslistmap(comf, filesmap, machines, 'clustermgr', args)
    process_commandslist_setenv(comf, args, machines, commandslist)
    dirmap.clear()
    filesmap.clear()
    del commandslist[:]

def output_info(comf, str):
    comf.write("cat <<EOF\n")
    comf.write("%s\n" % str)
    comf.write("EOF\n")

def generate_server_startstop(args, machines, node, idx, filesmap):
    mach = machines.get(node['ip'])
    serverdir = "kunlun-server-%s" % args.product_version
    envfname = 'env.sh.node'
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
    envfname = 'env.sh.node'
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
    envfname = 'env.sh.node'
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

def generate_hdfs_coresite_xml(args, host, port):
    url = "hdfs://%s:%d" % (host, port)
    coref = open('clustermgr/core-site.xml', 'w')
    coref.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    coref.write('<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>\n')
    coref.write('<configuration>\n')
    coref.write('<property>\n')
    coref.write('<name>fs.defaultFS</name>\n')
    coref.write('<value>%s</value>\n' % url)
    coref.write('</property>\n')
    coref.write('</configuration>\n')
    coref.close()

def generate_node_env(comf, args, machines, ip, idx):
    mach = machines.get(ip)
    filemap = get_3rdpackages_filemap(args)
    jdkdir = filemap['jdk'][1]
    hadoopdir = filemap['hadoop'][1]
    haproxydir = filemap['haproxy'][1]
    prometheusdir = filemap['prometheus'][1]
    filebeatdir = filemap['filebeat'][1]
    es_file = filemap['elasticsearch'][0]
    kibana_file = filemap['kibana'][0]
    mysqldriver_file = filemap['mysql-driver'][0]
    mysqldriver_dir = filemap['mysql-driver'][1]
    fname = '%d-env.sh.node' % idx
    fname_to = 'env.sh.node'
    envf = open('clustermgr/%s' % fname, 'w')
    #envf.write("#! /bin/bash\n")
    envf.write("export JDK_DIR=%s; #KUNLUN_SET_ENV\n" % jdkdir)
    envf.write("export HADOOP_DIR=%s; #KUNLUN_SET_ENV\n" % hadoopdir)
    envf.write("export HAPROXY_DIR=%s; #KUNLUN_SET_ENV\n" % haproxydir)
    envf.write("export FILEBEAT_DIR=%s; #KUNLUN_SET_ENV\n" % filebeatdir)
    envf.write("export PROMETHEUS_DIR=%s; #KUNLUN_SET_ENV\n" % prometheusdir)
    envf.write("export MYSQLDRIVER_DIR=%s; #KUNLUN_SET_ENV\n" % mysqldriver_dir)
    envf.write("export ES_FILE=%s; #KUNLUN_SET_ENV\n" % es_file)
    envf.write("export KIBANA_FILE=%s; #KUNLUN_SET_ENV\n" % kibana_file)
    envf.write("export MYSQLDRIVER_FILE=%s; #KUNLUN_SET_ENV\n" % mysqldriver_file)
    envf.write("export KUNLUN_VERSION=%s; #KUNLUN_SET_ENV\n" % args.product_version)
    envf.write("JAVA_HOME=%s/program_binaries/%s; #KUNLUN_SET_ENV\n" % (mach['basedir'], jdkdir))
    envf.write("PATH=$JAVA_HOME/bin:$PATH; #KUNLUN_SET_ENV\n")
    envf.write("HADOOP_HOME=%s/program_binaries/%s; #KUNLUN_SET_ENV\n" % (mach['basedir'], hadoopdir))
    envf.write("PATH=$HADOOP_HOME/bin:$PATH; #KUNLUN_SET_ENV\n")
    envf.write("FILEBEAT_HOME=%s/program_binaries/%s; #KUNLUN_SET_ENV\n" % (mach['basedir'], filebeatdir))
    envf.write("PATH=$FILEBEAT_HOME:$PATH; #KUNLUN_SET_ENV\n")
    envf.write("export JAVA_HOME; #KUNLUN_SET_ENV\n")
    envf.write("export HADOOP_HOME; #KUNLUN_SET_ENV\n")
    envf.write("export FILEBEAT_HOME; #KUNLUN_SET_ENV\n")
    envf.write("export PATH; #KUNLUN_SET_ENV\n")
    envf.close()
    process_file(comf, args, machines, ip, 'clustermgr/%s' % fname, '%s/%s' % (mach['basedir'],fname_to))

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

def setup_nodemgr_commands(args, idx, machines, node, commandslist, dirmap, filesmap, metaseeds, hasHDFS):
    cmdpat = "bash change_config.sh %s \"%s\" \"%s\"\n"
    nodemgrdir = "kunlun-node-manager-%s" % args.product_version
    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    proxysqldir = "kunlun-proxysql-%s" % args.product_version
    confpath = "%s/conf/node_mgr.cnf" % nodemgrdir
    mach = machines.get(node['ip'])
    if hasHDFS:
        addNodeToFilesListMap(filesmap, node, "core-site.xml", '.')
    targetdir = "program_binaries"
    if not args.cloud:
        addNodeToFilesListMap(filesmap, node, "%s.tgz" % storagedir, targetdir)
        addNodeToFilesListMap(filesmap, node, "%s.tgz" % serverdir, targetdir)
        addNodeToFilesListMap(filesmap, node, "%s.tgz" % proxysqldir, targetdir)
        addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf %s.tgz" % storagedir)
        addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf %s.tgz" % serverdir)
        addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf %s.tgz" % proxysqldir)
        #addToCommandsList(commandslist, node['ip'], targetdir, "rm -f %s.tgz" % storagedir)
        #addToCommandsList(commandslist, node['ip'], targetdir, "rm -f %s.tgz" % serverdir)
        #addToCommandsList(commandslist, node['ip'], targetdir, "rm -f %s.tgz" % proxysqldir)
    comstr = "test -d etc && echo > etc/instances_list.txt 2>/dev/null; exit 0"
    addToCommandsList(commandslist, node['ip'], "%s/%s" %(targetdir, storagedir), comstr)
    addToCommandsList(commandslist, node['ip'], "%s/%s" %(targetdir, serverdir), comstr)
    addToCommandsList(commandslist, node['ip'], "%s/%s/lib" %(targetdir, storagedir), "bash %s/process_deps.sh" % mach['basedir'])
    addToCommandsList(commandslist, node['ip'], "%s/%s/lib" %(targetdir, serverdir), "bash %s/process_deps.sh" % mach['basedir'])
    addToCommandsList(commandslist, node['ip'], "%s/%s/lib" %(targetdir, proxysqldir), "bash %s/process_deps.sh" % mach['basedir'])
    if mach['haspg']:
        addNodeToFilesListMap(filesmap, node, "../install/build_driver_forpg.sh", '.')
        addToCommandsList(commandslist, node['ip'], ".", "cp -f %s/%s/resources/psycopg2-2.8.4.tar.gz ." %(targetdir, serverdir))
        addToCommandsList(commandslist, node['ip'], ".",  "bash %s/build_driver_forpg.sh %s 0" % (mach['basedir'], mach['basedir']), "computing")
    setup_mgr_common(args, commandslist, dirmap, filesmap, machines, node, targetdir, storagedir, serverdir)
    for item in ["server_datadirs", "storage_datadirs", "storage_logdirs", "storage_waldirs"]:
        nodedirs = node[item].strip()
        for d in nodedirs.split(","):
            addToDirMap(dirmap, node['ip'], d.strip())
    if not args.cloud:
        fmap = get_3rdpackages_filemap(args)
        hadoop_file = fmap['hadoop'][0]
        jdk_file = fmap['jdk'][0]
        filebeat_file = fmap['filebeat'][0]
        addNodeToFilesListMap(filesmap, node, hadoop_file, targetdir)
        addNodeToFilesListMap(filesmap, node, jdk_file, targetdir)
        addNodeToFilesListMap(filesmap, node, filebeat_file, targetdir)
        addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf %s" % hadoop_file)
        addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf %s" % jdk_file)
        addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf %s" % filebeat_file)
    if hasHDFS:
        addToCommandsList(commandslist, node['ip'], '.', "cp -f ./core-site.xml program_binaries/\\${HADOOP_DIR}/etc/hadoop")
    addToCommandsList(commandslist, node['ip'], nodemgrdir, "chmod a+x bin/util/*")
    addToCommandsList(commandslist, node['ip'], '.', 'cp -f env.sh.node %s/bin/extra.env' % nodemgrdir)
    addToCommandsList(commandslist, node['ip'], '.', 'cp -f env.sh.node program_binaries/%s/dba_tools/extra.env' % storagedir)
    if args.setbashenv:
        addToCommandsList(commandslist, node['ip'], '.', 'test -f env.sh.node && cat env.sh.node >> ~/.bashrc')
    script_name = "setup_nodemgr_%d.sh" % idx
    scriptf = open('clustermgr/%s' % script_name, 'w')
    scriptf.write("#! /bin/bash\n")
    scriptf.write(cmdpat % (confpath, 'meta_group_seeds', metaseeds))
    scriptf.write(cmdpat % (confpath, 'brpc_http_port', node['brpc_http_port']))
    scriptf.write(cmdpat % (confpath, 'nodemgr_tcp_port', node['tcp_port']))
    scriptf.write(cmdpat % (confpath, 'local_ip', node['ip']))
    scriptf.write(cmdpat % (confpath, 'program_binaries_path', '%s/program_binaries' % mach['basedir']))
    scriptf.write(cmdpat % (confpath, 'instance_binaries_path', '%s/instance_binaries' % mach['basedir']))
    scriptf.write(cmdpat % (confpath, 'prometheus_path', '%s/program_binaries/${PROMETHEUS_DIR}' % mach['basedir']))
    scriptf.write(cmdpat % (confpath, 'storage_prog_package_name', storagedir))
    scriptf.write(cmdpat % (confpath, 'computer_prog_package_name', serverdir))
    if check_version_to_minor(args.product_version, 1, 1):
        scriptf.write(cmdpat % (confpath, 'proxysql_prog_package_name', proxysqldir))
    if 'prometheus_port_start' in node:
        scriptf.write(cmdpat % (confpath, 'prometheus_port_start', node['prometheus_port_start']))
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
    cmdpat = "bash change_config.sh %s \"%s\" \"%s\"\n"
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version
    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    confpath = "%s/conf/cluster_mgr.cnf" % clustermgrdir
    mach = machines.get(node['ip'])
    targetdir = "program_binaries"
    if initcommon:
        setup_mgr_common(args, commandslist, dirmap, filesmap, machines, node, targetdir, storagedir, serverdir)
    script_name = "setup_clustermgr_%d.sh" % idx
    scriptf = open('clustermgr/%s' % script_name, 'w')
    scriptf.write("#! /bin/bash\n")
    scriptf.write(cmdpat % (confpath, 'meta_group_seeds', metaseeds))
    scriptf.write(cmdpat % (confpath, 'brpc_raft_port', node['brpc_raft_port']))
    scriptf.write(cmdpat % (confpath, 'brpc_http_port', node['brpc_http_port']))
    scriptf.write(cmdpat % (confpath, 'local_ip', node['ip']))
    scriptf.write(cmdpat % (confpath, 'raft_group_member_init_config', initmember))
    scriptf.write(cmdpat % (confpath, 'prometheus_path', '%s/program_binaries/${PROMETHEUS_DIR}' % mach['basedir']))
    if 'prometheus_port_start' in node:
        scriptf.write(cmdpat % (confpath, 'prometheus_port_start', node['prometheus_port_start']))
    if 'brpc_raft_election_timeout_ms' in node:
        scriptf.write(cmdpat % (confpath, 'brpc_raft_election_timeout_ms', node['brpc_raft_election_timeout_ms']))
    scriptf.close()
    addNodeToFilesListMap(filesmap, node, script_name, '.')
    addToCommandsList(commandslist, node['ip'], '.', "bash ./%s" % script_name)

def install_clustermgr(args):
    if args.multipledc:
        install_clustermgr_multidc(args)
    else:
        install_clustermgr_onedc(args)

def install_clustermgr_onedc(args):
    install_clustermgr_int(args, setup_machines2, validate_and_set_config2)

def install_clustermgr_multidc(args):
    install_clustermgr_int(args, setup_machines3, validate_and_set_config3)

def install_clustermgr_int(args, machine_func, validate_func):
    jscfg = get_json_from_file(args.config)
    machines = {}
    machine_func(jscfg, machines, args)
    validate_func(jscfg, machines, args)
    comf = open(r'clustermgr/install.sh', 'w')
    comf.write('#! /bin/bash\n')
    comf.write("cat /dev/null > runlog\n")
    comf.write("cat /dev/null > lastlog\n")
    if args.verbose:
        comf.write("trap 'cat lastlog' DEBUG\n")
        comf.write("trap 'exit 1' ERR\n")
    else:
        comf.write("trap 'cat lastlog >> runlog' DEBUG\n")
        comf.write("trap 'cat lastlog; exit 1' ERR\n")
    install_with_config(jscfg, comf, machines, args)
    output_info(comf, "Installation completed !")
    comf.close()

def stop_clustermgr(args):
    if args.multipledc:
        stop_clustermgr_multidc(args)
    else:
        stop_clustermgr_onedc(args)

def stop_clustermgr_onedc(args):
    stop_clustermgr_int(args, setup_machines2, validate_and_set_config2)

def stop_clustermgr_multidc(args):
    stop_clustermgr_int(args, setup_machines3, validate_and_set_config3)

def stop_clustermgr_int(args, machine_func, validate_func):
    jscfg = get_json_from_file(args.config)
    machines = {}
    machine_func(jscfg, machines, args)
    validate_func(jscfg, machines, args)
    comf = open(r'clustermgr/stop.sh', 'w')
    comf.write('#! /bin/bash\n')
    comf.write("cat /dev/null > runlog\n")
    comf.write("cat /dev/null > lastlog\n")
    if args.verbose:
        comf.write("trap 'cat lastlog' DEBUG\n")
    else:
        comf.write("trap 'cat lastlog >> runlog' DEBUG\n")
    stop_with_config(jscfg, comf, machines, args)
    output_info(comf, "Stop action completed !")
    comf.close()

def start_clustermgr(args):
    if args.multipledc:
        start_clustermgr_multidc(args)
    else:
        start_clustermgr_onedc(args)

def start_clustermgr_onedc(args):
    start_clustermgr_int(args, setup_machines2, validate_and_set_config2)

def start_clustermgr_multidc(args):
    start_clustermgr_int(args, setup_machines3, validate_and_set_config3)

def start_clustermgr_int(args, machine_func, validate_func):
    jscfg = get_json_from_file(args.config)
    machines = {}
    machine_func(jscfg, machines, args)
    validate_func(jscfg, machines, args)
    comf = open(r'clustermgr/start.sh', 'w')
    comf.write('#! /bin/bash\n')
    comf.write("cat /dev/null > runlog\n")
    comf.write("cat /dev/null > lastlog\n")
    if args.verbose:
        comf.write("trap 'cat lastlog' DEBUG\n")
    else:
        comf.write("trap 'cat lastlog >> runlog' DEBUG\n")
    start_with_config(jscfg, comf, machines, args)
    output_info(comf, "Start action completed !")
    comf.close()

def clean_clustermgr(args):
    if args.multipledc:
        clean_clustermgr_multidc(args)
    else:
        clean_clustermgr_onedc(args)

def clean_clustermgr_onedc(args):
    clean_clustermgr_int(args, setup_machines2, validate_and_set_config2)

def clean_clustermgr_multidc(args):
    clean_clustermgr_int(args, setup_machines3, validate_and_set_config3)

def clean_clustermgr_int(args, machine_func, validate_func):
    jscfg = get_json_from_file(args.config)
    machines = {}
    machine_func(jscfg, machines, args)
    validate_func(jscfg, machines, args)
    comf = open(r'clustermgr/clean.sh', 'w')
    comf.write('#! /bin/bash\n')
    comf.write("cat /dev/null > runlog\n")
    comf.write("cat /dev/null > lastlog\n")
    if args.verbose:
        comf.write("trap 'cat lastlog' DEBUG\n")
    else:
        comf.write("trap 'cat lastlog >> runlog' DEBUG\n")
    clean_with_config(jscfg, comf, machines, args)
    output_info(comf, "Clean action completed !")
    comf.close()

def service_clustermgr(args):
    if args.multipledc:
        service_clustermgr_multidc(args)
    else:
        service_clustermgr_onedc(args)

def service_clustermgr_onedc(args):
    service_clustermgr_int(args, setup_machines2, validate_and_set_config2)

def service_clustermgr_multidc(args):
    service_clustermgr_int(args, setup_machines3, validate_and_set_config3)

def service_clustermgr_int(args, machine_func, validate_func):
    jscfg = get_json_from_file(args.config)
    machines = {}
    machine_func(jscfg, machines, args)
    validate_func(jscfg, machines, args)
    comf = open(r'clustermgr/service.sh', 'w')
    comf.write('#! /bin/bash\n')
    comf.write("cat /dev/null > runlog\n")
    comf.write("cat /dev/null > lastlog\n")
    if args.verbose:
        comf.write("trap 'cat lastlog' DEBUG\n")
    else:
        comf.write("trap 'cat lastlog >> runlog' DEBUG\n")
    service_with_config(jscfg, comf, machines, args)
    output_info(comf, "Service action completed !")
    comf.close()

def setup_mgr_common(args, commandslist, dirmap, filesmap, machines, node, targetdir, storagedir, serverdir):
    mach = machines.get(node['ip'])
    addToDirMap(dirmap, node['ip'], "%s/%s" % (mach['basedir'], targetdir))
    addToDirMap(dirmap, node['ip'], "%s/%s/util" % (mach['basedir'], targetdir))
    addToDirMap(dirmap, node['ip'], "%s/instance_binaries" % mach['basedir'])
    addToDirMap(dirmap, node['ip'], "%s/instance_binaries/storage" % mach['basedir'])
    addToDirMap(dirmap, node['ip'], "%s/instance_binaries/computer" % mach['basedir'])
    if not args.cloud:
        fmap = get_3rdpackages_filemap(args)
        prome_file = fmap['prometheus'][0]
        addNodeToFilesListMap(filesmap, node, prome_file, targetdir)
        addToCommandsList(commandslist, node['ip'], targetdir, "tar -xzf %s" % prome_file)
        #addToCommandsList(commandslist, node['ip'], targetdir, "rm -f %s.tgz" % storagedir)
        #addToCommandsList(commandslist, node['ip'], targetdir, "tar -czf %s.tgz %s" % (storagedir, storagedir))
        #addToCommandsList(commandslist, node['ip'], targetdir, "rm -f %s.tgz" % serverdir)
        #addToCommandsList(commandslist, node['ip'], targetdir, "tar -czf %s.tgz %s" % (serverdir, serverdir))

def get_haproxy_ips(jscfg):
    haproxyips = set()
    if 'cluster' not in jscfg:
        return haproxyips
    for cluster in clusters:
        if 'haproxy' in cluster:
            haproxyips.add(cluster['haproxy']['ip'])
    return haproxyips

def get_xpanel_ips(jscfg):
    xpanelips = set()
    if 'xpanel' not in jscfg:
        return xpanelips
    for node in jscfg['xpanel']['nodes']:
        xpanelips.add(node['ip'])
    return xpanelips

def setup_xpanel(jscfg, machines, comf, args):
    if 'xpanel' not in jscfg:
        return
    xpanel = jscfg['xpanel']
    for node in xpanel['nodes']:
        if xpanel['imageType'] == 'file':
            if not args.cloud:
                output_info(comf, "transfering xpanel package to %s ..." % node['ip'])
                process_command_noenv(comf, args, machines, node['ip'], '/',
                    'sudo mkdir -p %s && sudo chown -R %s:\`id -gn %s\` %s' % (mach['basedir'],
                    mach['user'], mach['user'], mach['basedir']))
                process_file(comf, args, machines, node['ip'], 'clustermgr/%s' % xpanel['imageFile'], mach['basedir'])
            cmdpat = "sudo docker inspect %s >& /dev/null || ( gzip -cd %s | sudo docker load )"
            process_command_noenv(comf, args, machines, node['ip'], mach['basedir'], 
                    cmdpat % (xpanel['image'], xpanel['imageFile']))

def install_xpanel(jscfg, machines, dirmap, filesmap, commandslist, metaseeds, comf, args):
    if 'xpanel' not in jscfg:
        return
    xpanel = jscfg['xpanel']
    restart = 'no'
    if args.autostart:
        restart = 'always'
    for node in xpanel['nodes']:
        mach = machines.get(node['ip'])
        output_info(comf, "setup xpanel on %s ..." % node['ip'])
        cmdpat = "sudo docker run -itd --restart={} --env METASEEDS=%s --name %s -p %d:80 %s bash -c '/bin/bash /kunlun/start.sh'".format(restart)
        process_command_noenv(comf, args, machines, node['ip'], '/', cmdpat % (metaseeds, node['name'], node['port'], xpanel['image']))

def stop_xpanel(jscfg, machines, dirmap, filesmap, commandslist, comf, args):
    if 'xpanel' not in jscfg:
        return
    xpanel = jscfg['xpanel']
    for node in xpanel['nodes']:
        output_info(comf, "Stopping xpanel on %s ..." % node['ip'])
        cmdpat = "sudo docker container stop -f %s"
        process_command_noenv(comf, args, machines, node['ip'], '/', cmdpat % node['name'])

def start_xpanel(jscfg, machines, dirmap, filesmap, commandslist, comf, args):
    if 'xpanel' not in jscfg:
        return
    xpanel = jscfg['xpanel']
    for node in xpanel['nodes']:
        output_info(comf, "Starting xpanel on %s ..." % node['ip'])
        cmdpat = "sudo docker container start %s"
        process_command_noenv(comf, args, machines, node['ip'], '/', cmdpat % node['name'])

def clean_xpanel(jscfg, machines, dirmap, filesmap, commandslist, comf, args):
    if 'xpanel' not in jscfg:
        return
    xpanel = jscfg['xpanel']
    for node in xpanel['nodes']:
        output_info(comf, "Cleaning xpanel on %s ..." % node['ip'])
        cmdpat = "sudo docker container rm -f %s"
        process_command_noenv(comf, args, machines, node['ip'], '/', cmdpat % node['name'])
        cmdpat = "sudo docker image rm -f %s"
        process_command_noenv(comf, args, machines, node['ip'], '/', cmdpat % xpanel['image'])
        if xpanel['imageType'] == 'file' and not args.cloud:
            mach = machines.get(node['ip'])
            process_command_noenv(comf, args, machines, node['ip'], mach['basedir'], 'rm -f %s' % xpanel['imageFile'])

def setup_elasticsearch(jscfg, machines, comf, args):
    if 'elasticsearch' not in jscfg:
        return
    node = jscfg['elasticsearch']
    mach = machines.get(node['ip'])
    fmap = get_3rdpackages_filemap(args)
    es_pack = fmap['elasticsearch'][0]
    k_pack = fmap['kibana'][0]
    if not args.cloud:
        output_info(comf, "transfering elasticsearch and kibana package to %s ..." % node['ip'])
        process_command_noenv(comf, args, machines, node['ip'], '/',
                'sudo mkdir -p %s && sudo chown -R %s:\`id -gn %s\` %s' % (mach['basedir'],
            mach['user'], mach['user'], mach['basedir']))
        process_file(comf, args, machines, node['ip'], 'clustermgr/%s' % es_pack, mach['basedir'])
        process_file(comf, args, machines, node['ip'], 'clustermgr/%s' % k_pack, mach['basedir'])

def install_elasticsearch(jscfg, machines, metaseeds, comf, args):
    if 'elasticsearch' not in jscfg:
        return
    node = jscfg['elasticsearch']
    mach = machines.get(node['ip'])
    fmap = get_3rdpackages_filemap(args)
    es_image = fmap['elasticsearch'][1]
    k_image = fmap['kibana'][1]
    es_port = node['port']
    k_port = node['kibana_port']
    output_info(comf, "install elasticsearch and kibana on %s ..." % node['ip'])
    cmdpat = "sudo docker inspect %s >& /dev/null || ( gzip -cd %s | sudo docker load )"
    process_command_setenv(comf, args, machines, node['ip'], mach['basedir'], cmdpat % (es_image, "\\${ES_FILE}"))
    process_command_setenv(comf, args, machines, node['ip'], mach['basedir'], cmdpat % (k_image, "\\${KIBANA_FILE}"))
    restart = 'no'
    if args.autostart:
        restart = 'always'
    cmdpat = "sudo docker run -itd --restart={} --name elasticsearch_%d  -p %d:9200 -e discovery.type=single-node %s".format(restart)
    process_command_noenv(comf, args, machines, node['ip'], mach['basedir'], cmdpat % (es_port, es_port, es_image))
    cmdpat = "sudo docker run -itd --restart={} --name kibana_%d  -p %d:5601 -e ELASTICSEARCH_HOSTS=http://%s:%d %s".format(restart)
    process_command_noenv(comf, args, machines, node['ip'], mach['basedir'], cmdpat % (k_port, k_port, node['ip'], es_port, k_image))
    es_host = "%s:%d" % (node['ip'], es_port)
    k_host = "%s:%d" % (node['ip'], k_port)
    for node in jscfg['node_manager']['nodes']:
        mach = machines.get(node['ip'])
        targetdir = "%s/program_binaries/\\${FILEBEAT_DIR}" % mach['basedir']
        cmdpat = "sed -i 's/localhost:9200/%s/g' filebeat.yml"
        process_command_setenv(comf, args, machines, node['ip'], targetdir, cmdpat % es_host)
        cmdpat = "sed -i '/localhost:5601/s/#host/host/g' filebeat.yml"
        process_command_setenv(comf, args, machines, node['ip'], targetdir, cmdpat)
        cmdpat = "sed -i 's/localhost:5601/%s/g' filebeat.yml"
        process_command_setenv(comf, args, machines, node['ip'], targetdir, cmdpat % k_host)

def start_elasticsearch(jscfg, machines, comf, args):
    if 'elasticsearch' not in jscfg:
        return
    node = jscfg['elasticsearch']
    mach = machines.get(node['ip'])
    es_port = node['port']
    k_port = node['kibana_port']
    output_info(comf, "start elasticsearch and kibana on %s ..." % node['ip'])
    cmdpat = "sudo docker container start kibana_%d"
    process_command_noenv(comf, args, machines, node['ip'], mach['basedir'], cmdpat % k_port)
    cmdpat = "sudo docker container start elasticsearch_%d"
    process_command_noenv(comf, args, machines, node['ip'], mach['basedir'], cmdpat % es_port)

def stop_elasticsearch(jscfg, machines, comf, args):
    if 'elasticsearch' not in jscfg:
        return
    node = jscfg['elasticsearch']
    mach = machines.get(node['ip'])
    es_port = node['port']
    k_port = node['kibana_port']
    output_info(comf, "stop elasticsearch and kibana on %s ..." % node['ip'])
    cmdpat = "sudo docker container stop kibana_%d"
    process_command_noenv(comf, args, machines, node['ip'], mach['basedir'], cmdpat % k_port)
    cmdpat = "sudo docker container stop elasticsearch_%d"
    process_command_noenv(comf, args, machines, node['ip'], mach['basedir'], cmdpat % es_port)

def clean_elasticsearch(jscfg, machines, metaseeds, comf, args):
    if 'elasticsearch' not in jscfg:
        return
    node = jscfg['elasticsearch']
    mach = machines.get(node['ip'])
    fmap = get_3rdpackages_filemap(args)
    es_image = fmap['elasticsearch'][1]
    es_port = node['port']
    k_image = fmap['kibana'][1]
    k_port = node['kibana_port']
    output_info(comf, "clean elasticsearch and kibana on %s ..." % node['ip'])
    cmdpat = "sudo docker container rm -f kibana_%d"
    process_command_noenv(comf, args, machines, node['ip'], mach['basedir'], cmdpat % k_port)
    cmdpat = "sudo docker container rm -f elasticsearch_%d"
    process_command_noenv(comf, args, machines, node['ip'], mach['basedir'], cmdpat % es_port)
    cmdpat = 'sudo docker image rm -f %s'
    process_command_noenv(comf, args, machines, node['ip'], mach['basedir'], cmdpat % k_image)
    process_command_noenv(comf, args, machines, node['ip'], mach['basedir'], cmdpat % es_image)
    # Removing the image files will be added later.

def get_cluster_memo_asjson(cluster):
    comps = cluster['comp']['nodes']
    mobj = {
            "comps": str(len(comps)),
            "computer_passwd": comps[0]['password'],
            "computer_user": comps[0]['user'],
            "cpu_cores": str(cluster['storage_cpu_cores']),
            "dbcfg": str(cluster['dbcfg']),
            'fullsync_level': str(cluster['fullsync_level']),
            "ha_mode": cluster['ha_mode'],
            "innodb_size": str(cluster['innodb_buffer_pool_size_MB']),
            "max_connections": str(cluster['max_connections']),
            "max_storage_size": str(cluster['max_storage_size_GB']),
            "nodes": str(len(cluster['data'][0]['nodes'])),
            "shards": str(len(cluster['data']))
            }
    return mobj

def install_clusters(jscfg, machines, dirmap, filesmap, commandslist, reg_metaname, metaseeds, comf, metaobj, args):
    if 'clusters' not in jscfg or len(jscfg['clusters']) == 0:
        return
    if args.multipledc:
        my_print("skip cluster operation for multiple dc")
        return
    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    clusters = jscfg['clusters']
    meta_hamode = jscfg['meta']['ha_mode']
    
    if 'nodemapmaster' not in metaobj:
        metaobj['nodemapmaster'] = {'op':'add', "elements":[]}
    elements = metaobj['nodemapmaster']["elements"]
    memoeles = []
    metaobj['cluster_info'] = {'op':'add', 'elements': memoeles}
    vareles = metaobj['set_variables']['elements']

    i = 1
    for cluster in clusters:
        cluster_name = cluster['name']
        output_info(comf, "installing cluster %s ..." % cluster_name)
        for shard in cluster['data']:
            for node in shard['nodes']:
                setup_storage_env(node, machines, dirmap, commandslist, args)
        for node in cluster['comp']['nodes']:
            setup_server_env(node, machines, dirmap, commandslist, args)
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)
        memo_obj = get_cluster_memo_asjson(cluster)
        memoeles.append({"name": cluster_name, "memo": memo_obj})
        # Storage nodes
        cmdpat = 'python2 install-mysql.py --config=./%s --target_node_index=%d --cluster_id=%s --shard_id=%s --server_id=%d'
        cmdpat += ' --meta_addrs=%s ' % metaseeds
        if cluster['storage_template'] == 'small':
            cmdpat += ' --dbcfg=./template-small.cnf'
        extraopt = " --ha_mode=%s" % cluster['ha_mode']
        j = 1
        pries = []
        secs = []
        pairs = []
        for shard in cluster['data']:
            if not 'group_uuid' in shard:
                shard['group_uuid'] = getuuid()
            shard_id = "shard_%d" % i
            my_shardname = "cluster%d_shard%d.json" % (i,j)
            shardf = open(r'clustermgr/%s' % my_shardname, 'w')
            json.dump(shard, shardf, indent=4)
            shardf.close()
            k = 0
            pnode = None
            snodes = []
            for node in shard['nodes']:
                if 'fullsync_level' in cluster and cluster['fullsync_level'] != 1:
                    vareles.append({"ip": node['ip'], 'port':node['port'],
                        'variable_name':'fullsync_consistency_level',
                        "type":"integer", 'value':cluster['fullsync_level']})
                targetdir='%s/%s/dba_tools' % (node['program_dir'], storagedir)
                addNodeToFilesListMap(filesmap, node, my_shardname, targetdir)
                mach = machines.get(node['ip'])
                cmd = cmdpat % (my_shardname, k, cluster_name, shard_id, k+1)
                generate_storage_startstop(args, machines, node, k, filesmap)
                if node.get('is_primary', False):
                    pnode = node
                    vareles.append({"ip": node['ip'], 'port':node['port'],
                        'variable_name':'ha_role', "type":"integer", 'value': 1})
                    pairs.append({"node":node, "cfg": my_shardname})
                    pries.append([node['ip'], targetdir, cmd])
                else:
                    secs.append([node['ip'], targetdir, cmd])
                    snodes.append(node)
                addToDirMap(dirmap, node['ip'], node['data_dir_path'])
                addToDirMap(dirmap, node['ip'], node['log_dir_path'])
                addToDirMap(dirmap, node['ip'], node['innodb_log_dir_path'])
                k += 1
            for node in snodes:
                elements.append({"host": node['ip'], "port":node['port'], 
                    "master_host":pnode['ip'], "master_port":pnode['port'], "is_meta": False})
            j += 1

        for item in pries:
            addToCommandsList(commandslist, item[0], item[1], item[2] + extraopt, "storage")
        for item in secs:
            addToCommandsList(commandslist, item[0], item[1], item[2] + extraopt, "storage")

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
            obj = {'shard_name': 'shard_%d' % j}
            j += 1
            nodes = []
            for node in shard['nodes']:
                n = {'user':'pgx', 'password':'pgx_pwd'}
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

        node = cluster['comp']['nodes'][0]
        targetdir='%s/%s/scripts' % (node['program_dir'], serverdir)
        addNodeToFilesListMap(filesmap, node, pg_compname, targetdir)
        addNodeToFilesListMap(filesmap, node, reg_metaname, targetdir)
        addNodeToFilesListMap(filesmap, node, reg_shardname, targetdir)
        cmdpat='python2 create_cluster.py --shards_config=./%s \
--comps_config=./%s  --meta_config=./%s --cluster_name=%s --meta_ha_mode=%s --ha_mode=%s --cluster_owner=abc --cluster_biz=%s'
        addToCommandsList(commandslist, node['ip'], targetdir,
            cmdpat % (reg_shardname, pg_compname, reg_metaname, cluster_name, meta_hamode, cluster['ha_mode'], cluster_name), "parent")

        cmdpat = r'%spython2 add_comp_self.py  --meta_config=./%s --cluster_name=%s --user=%s --password=%s --hostname=%s --port=%d --mysql_port=%d --datadir=%s --install --ha_mode=%s'
        idx=0
        for node in cluster['comp']['nodes']:
            targetdir='%s/%s/scripts' % (node['program_dir'], serverdir)
            addNodeToFilesListMap(filesmap, node, reg_metaname, targetdir)
            mach = machines.get(node['ip'])
            absenvfname = '%s/env.sh.node' % (mach['basedir'])
            envpfx = "test -f %s && . %s; " % (absenvfname, absenvfname)
            addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (envpfx, reg_metaname, cluster_name,
                node['user'], node['password'], node['ip'], node['port'], node['mysql_port'], node['datadir'], meta_hamode), "parent")
            addToDirMap(dirmap, node['ip'], node['datadir'])
            generate_server_startstop(args, machines, node, idx, filesmap)
            idx += 1
        if 'haproxy' in cluster:
            node = cluster['haproxy']
            confname = '%d-haproxy-%d.cfg' % (i, node['port'])
            targetconfname = 'haproxy-%d.cfg' % node['port']
            generate_haproxy_config(cluster, machines, 'clustermgr', confname)
            addNodeToFilesListMap(filesmap, node, confname, targetconfname)
            cmdpat = "\\${HAPROXY_DIR}/sbin/haproxy -f %s >& haproxy-%d.log" % (targetconfname, node['port'])
            addToCommandsList(commandslist, node['ip'], ".", cmdpat)
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)
        i += 1

def start_clusters(clusters, nodemgrmaps, machines, comf, args):
    if args.multipledc:
        my_print("skip cluster operation for multiple dc")
        return
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
        if 'haproxy' in cluster:
            node = cluster['haproxy']
            targetconfname = 'haproxy-%d.cfg' % node['port']
            cmdpat = "\\${HAPROXY_DIR}/sbin/haproxy -f %s >& haproxy-%d.log" % (targetconfname, node['port'])
            addToCommandsList(commandslist, node['ip'], ".", cmdpat)
    process_commandslist_setenv(comf, args, machines, commandslist)

def stop_clusters(clusters, nodemgrmaps, machines, comf, args):
    if args.multipledc:
        my_print("skip cluster operation for multiple dc")
        return
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
        if 'haproxy' in cluster:
            node = cluster['haproxy']
            cmdpat="cat haproxy-%d.pid | xargs kill -9" % node['port']
            addToCommandsList(commandslist, node['ip'], ".", cmdpat)
    process_commandslist_setenv(comf, args, machines, commandslist)

def clean_clusters(args, clusters, nodemgrmaps, machines, comf):
    if args.multipledc:
        my_print("skip cluster operation for multiple dc")
        return None
    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    commandslist = []
    targetdir = '.'
    names = []
    for cluster in clusters:
        names.append(cluster['name'])
        for shard in cluster['data']:
            for node in shard['nodes']:
                nodemgrobj = nodemgrmaps.get(node['ip'])
                if not nodemgrobj['skip']:
                    continue
                cmdpat = r'bash stopmysql.sh %d'
                targetdir = "%s/%s/dba_tools" % (node['program_dir'], storagedir)
                addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (node['port']))
                cmdpat = r'rm -fr %s'
                addToCommandsList(commandslist, node['ip'], '.', cmdpat % (node['data_dir_path']))
                addToCommandsList(commandslist, node['ip'], '.', cmdpat % (node['log_dir_path']))
                addToCommandsList(commandslist, node['ip'], '.', cmdpat % (node['innodb_log_dir_path']))
        for node in cluster['comp']['nodes']:
            nodemgrobj = nodemgrmaps.get(node['ip'])
            if not nodemgrobj['skip']:
                continue
            targetdir = "%s/%s/dba_tools" % (node['program_dir'], serverdir)
            cmdpat = r'python2 stop_pg.py --port=%d'
            addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % (node['port']))
            cmdpat = r'rm -fr %s'
            addToCommandsList(commandslist, node['ip'], '.', cmdpat % (node['datadir']))
        if 'haproxy' in cluster:
            node = cluster['haproxy']
            cmdpat="cat haproxy-%d.pid | xargs kill -9" % node['port']
            addToCommandsList(commandslist, node['ip'], ".", cmdpat)
    process_commandslist_setenv(comf, args, machines, commandslist)
    return names

def setup_metanodes_multidc(jscfg, metanodes, my_metaname, metaobj):
    # We need to reorder the meta nodes order, so that the install order is:
    #    - meta nodes in primary dc(master first)
    #    - meta nodes in secondary dc(also master first, then replicas)
    #    - meta nodes in standby dc(like above)
    meta = jscfg['meta']
    dcprimary = jscfg['dcprimary']
    dcsecondarylist = jscfg['dcsecondarylist']
    dcstandbylist = jscfg['dcstandbylist']
    dc_meta_map = jscfg['dc_meta_map']
    i = 0
    if len(meta['nodes']) > 0:
        j = 0
        elements = []
        meta['fullsync_level'] = len(dc_meta_map[dcprimary['name']]) + len(dcsecondarylist) - 1
        for node in dc_meta_map[dcprimary['name']]:
            fname = '%s.%d' % (my_metaname, i)
            metaf = open(r'clustermgr/%s' % fname, 'w')
            i += 1
            idx = j
            json.dump({"group_uuid": meta['group_uuid'], "nodes": dc_meta_map[dcprimary['name']]}, metaf, indent=4)
            metaf.close()
            metanodes.append({"node": node, "file": fname, "index": idx, "fullsync": 1})
            if j > 0:
                node0 = dc_meta_map[dcprimary['name']][0]
                elements.append({"host": node['ip'], "port": node['port'],
                    'master_host': node0['ip'], 'master_port': node0['port'], 'is_meta':True})
            j += 1
        pdcmaster = dc_meta_map[dcprimary['name']][0]
        pdcmasternode = {"ip": pdcmaster["ip"], "port": pdcmaster['port'], 'is_primary': True}
        sdcmaster = None
        for dc in dcsecondarylist:
            nodes = dc_meta_map[dc['name']]
            node0 = nodes[0]
            if sdcmaster is None:
                sdcmaster = node0
            fname = '%s.%d' % (my_metaname, i)
            metaf = open(r'clustermgr/%s' % fname, 'w')
            i += 1
            json.dump({"group_uuid": meta['group_uuid'], "nodes": [pdcmasternode, node0]}, metaf, indent=4)
            metaf.close()
            idx = 1
            metanodes.append({"node": node0, "file": fname, "index": idx, "fullsync": 1})
            elements.append({"host": node0['ip'], "port": node0['port'],
                'master_host': pdcmaster['ip'], 'master_port': pdcmaster['port'], 'is_meta':True})
            node0['is_primary'] = True
            for j in range(1, len(nodes)):
                fname = '%s.%d' % (my_metaname, i)
                metaf = open(r'clustermgr/%s' % fname, 'w')
                i += 1
                idx = j
                json.dump({"group_uuid": meta['group_uuid'], "nodes": nodes}, metaf, indent=4)
                node = nodes[j]
                metanodes.append({"node": node, "file": fname, "index": idx, "fullsync": 0})
                elements.append({"host": node['ip'], "port": node['port'],
                    'master_host': node0['ip'], 'master_port': node0['port'], 'is_meta':True})

        if sdcmaster is None:
            sdcmaster = dc_meta_map[dcprimary['name']][1]
        sdcmasternode = {"ip": sdcmaster["ip"], "port": sdcmaster['port'], 'is_primary': True}
        for dc in dcstandbylist:
            nodes = dc_meta_map[dc['name']]
            node0 = nodes[0]
            fname = '%s.%d' % (my_metaname, i)
            metaf = open(r'clustermgr/%s' % fname, 'w')
            i += 1
            json.dump({"group_uuid": meta['group_uuid'], "nodes": [sdcmasternode, node0]}, metaf, indent=4)
            metaf.close()
            idx = 1
            metanodes.append({"node": node0, "file": fname, "index": idx, "fullsync": 0})
            elements.append({"host": node0['ip'], "port": node0['port'],
                'master_host': sdcmasternode['ip'], 'master_port': sdcmasternode['port'], 'is_meta':True})
            node0['is_primary'] = True
            for j in range(1, len(nodes)):
                fname = '%s.%d' % (my_metaname, i)
                metaf = open(r'clustermgr/%s' % fname, 'w')
                i += 1
                idx = j
                json.dump({"group_uuid": meta['group_uuid'], "nodes": nodes}, metaf, indent=4)
                metanodes.append({"node": nodes[j], "file": fname, "index": idx, "fullsync": 0})
                elements.append({"host": node['ip'], "port": node['port'],
                    'master_host': node0['ip'], 'master_port': node0['port'], 'is_meta':True})
        metaobj['nodemapmaster'] = {"op":"add", "elements": elements}

def setup_metanodes_onedc(jscfg, metanodes, my_metaname, metaobj):
    meta = jscfg['meta']
    if len(meta) == 0:
        return
    metaf = open(r'clustermgr/%s' % my_metaname, 'w')
    json.dump(meta, metaf, indent=4)
    metaf.close()
    pnode = None
    mlen = len(meta['nodes'])
    for idx in range(0, mlen):
        node = meta['nodes'][idx]
        if node['is_primary']:
            metanodes.append({"node": node, "file":my_metaname, "index":idx, "fullsync":1})
            pnode = node
            break
    elements = []
    for idx in range(0, mlen):
        node = meta['nodes'][idx]
        if node['is_primary']:
            continue
        metanodes.append({"node": node, "file":my_metaname, "index":idx, "fullsync":1})
        elements.append({"host": node['ip'], "port": node['port'], "master_host": pnode['ip'], 
            "master_port": pnode['port'], "is_meta": True})
    metaobj['nodemapmaster'] = {'op':'add', 'elements': elements}

def install_with_config(jscfg, comf, machines, args):
    meta = jscfg['meta']
    clustermgr = jscfg['cluster_manager']
    nodemgr = jscfg['node_manager']
    meta_hamode = meta.get('ha_mode', '')
    storagedir = "kunlun-storage-%s" % args.product_version
    serverdir = "kunlun-server-%s" % args.product_version
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version
    nodemgrdir = "kunlun-node-manager-%s" % args.product_version

    cluster_name = 'meta'
    extraopt = " --ha_mode=%s" % meta_hamode
    metaseeds = meta['group_seeds']
    my_print('metaseeds:%s' % metaseeds)

    nodemgrmaps = {}
    nodemgrips = set()
    for node in nodemgr['nodes']:
        nodemgrmaps[node['ip']] = node
        nodemgrips.add(node['ip'])

    # TODO: we need to add priority here.
    clustermgrips = set()
    members=[]
    for node in clustermgr['nodes']:
        clustermgrips.add(node['ip'])
        members.append("%s:%d:0" % (node['ip'], node['brpc_raft_port']))
    initmember = clustermgr.get('raft_group_member_init_config', '')
    initmember = "%s%s," % (initmember, ",".join(members))
    my_print('raft_group_member_init_config:%s' % initmember)

    haproxyips = get_haproxy_ips(jscfg)
    workips = set()
    workips.update(nodemgrips)
    workips.update(clustermgrips)
    workips.update(haproxyips)
    if 'elasticsearch' in jscfg:
        workips.add(jscfg['elasticsearch']['ip'])
    # my_print("workips:%s" % str(workips))
    fmap = get_3rdpackages_filemap(args)
    #my_print(fmap)
    haproxy_file = fmap['haproxy'][0]

    output_info(comf, "initializing all working nodes ...")
    i = 0
    for ip in workips:
        mach = machines.get(ip)
        if args.sudo:
            process_command_noenv(comf, args, machines, ip, '/',
                'sudo mkdir -p %s && sudo chown -R %s:\`id -gn %s\` %s' % (mach['basedir'],
                    mach['user'], mach['user'], mach['basedir']))
        else:
            process_command_noenv(comf, args, machines, ip, '/', 'mkdir -p %s' % mach['basedir'])
        process_file(comf, args, machines, ip, 'clustermgr/env.sh.template', mach['basedir'])
        extstr = "sed -s 's#KUNLUN_BASEDIR#%s#g' env.sh.template > env.sh" % mach['basedir']
        process_command_noenv(comf, args, machines, ip, mach['basedir'], extstr)
        extstr = "sed -i 's#KUNLUN_VERSION#%s#g' env.sh" % args.product_version
        process_command_noenv(comf, args, machines, ip, mach['basedir'], extstr)
        process_file(comf, args, machines, ip, 'install/process_deps.sh', mach['basedir'])
        process_file(comf, args, machines, ip, 'install/change_config.sh', mach['basedir'])
        process_file(comf, args, machines, ip, 'install/build_driver_formysql.sh', mach['basedir'])
        if not args.cloud:
            process_file(comf, args, machines, ip, 'clustermgr/%s' % fmap['mysql-driver'][0], mach['basedir'])
            generate_node_env(comf, args, machines, ip, i)
        process_command_setenv(comf, args, machines, ip, mach['basedir'], 'bash ./build_driver_formysql.sh %s' % mach['basedir'])
        if ip in haproxyips and not args.cloud:
            process_file(comf, args, machines, ip, 'clustermgr/%s' % haproxy_file, mach['basedir'])
            process_command_noenv(comf, args, machines, ip, mach['basedir'], 'tar -xzf %s' % haproxy_file)
        i += 1

    setup_xpanel(jscfg, machines, comf, args)
    setup_elasticsearch(jscfg, machines, comf, args)

    dirmap = {}
    filesmap = {}
    commandslist = []

    # used for install storage nodes
    reg_metaname = 'reg_meta.json'
    xpanel_sqlfile = 'dba_tools_db.sql'
    if not 'group_uuid' in meta:
	    meta['group_uuid'] = getuuid()
    metaf = open(r'clustermgr/%s' % reg_metaname, 'w')
    objs = []
    for addr in metaseeds.split(','):
        parts = addr.split(':')
        obj = {}
        obj['is_primary'] = False
        obj['data_dir_path'] = ''
        obj['nodemgr_bin_path'] = ''
        obj['ip'] = parts[0]
        if len(parts) > 1:
            obj['port'] = int(parts[1])
        else:
            obj['port'] = 3306
        obj['user'] = "pgx"
        obj['password'] = "pgx_pwd"
        objs.append(obj)
    json.dump(objs, metaf, indent=4)
    metaf.close()

    my_metaname = 'mysql_meta.json'
    metaobj = {}
    metaobj['set_variables'] = {'op':'add', 'elements':[]}
    vareles = metaobj['set_variables']['elements']
    metanodes = []
    if args.multipledc:
        setup_metanodes_multidc(jscfg, metanodes, my_metaname, metaobj)
    else:
        setup_metanodes_onedc(jscfg, metanodes, my_metaname, metaobj)

    # process elastic search data.
    if 'elasticsearch' in jscfg:
        node = jscfg['elasticsearch']
        esobj = {
            "op": "add",
            "data": {
                "host": node['ip'],
                "port": node['port']
            }
        }
        metaobj['elasticsearch'] = esobj

    # process backup data
    hasHDFS = False
    if 'backup' in jscfg:
        node = jscfg['backup']
        if 'hdfs' in node:
            hasHDFS = True
            hdfs = node['hdfs']
            generate_hdfs_coresite_xml(args, hdfs['ip'], hdfs['port'])
            metaobj['hdfsbackup'] = {
                    "op": "add",
                    "data": {
                            "host": hdfs['ip'],
                            "port": hdfs['port']
                        }
                    }
        if 'ssh' in node:
            sshbackup = node['ssh']
            metaobj['sshbackup'] = {
                    "op": "add",
                    "data": {
                        "host": sshbackup['ip'],
                        "port": sshbackup['port'],
                        "user": sshbackup['user'],
                        "targetRoot": sshbackup['targetDir']
                        }
                    }

    # process datacenter data
    if 'datacenters' in jscfg and len(jscfg['datacenters']) > 0:
        metaobj['datacenters'] = { 'op': 'add', 'elements': jscfg['datacenters']}

   # bootstrap the cluster
    if len(nodemgr['nodes']) > 0:
        metaobj['node_manager'] = {'op': 'add', 'elements': nodemgr['nodes']}

    i = 0
    for node in nodemgr['nodes']:
        if node['skip']:
            continue
        mach = machines.get(node['ip'])
        output_info(comf, "setup node_mgr on %s ..." % node['ip'])
        install_nodemgr_env(comf, mach, machines, args)
        setup_nodemgr_commands(args, i, machines, node, commandslist, dirmap, filesmap, metaseeds, hasHDFS)
        generate_nodemgr_startstop(args, machines, node, i, filesmap)
        if args.autostart:
            generate_nodemgr_service(args, machines, commandslist, node, i, filesmap)
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)
        i += 1

    cmdpat = 'python2 install-mysql.py --config=./%s --target_node_index=%d --cluster_id=%s --shard_id=%s --server_id=%d --fullsync=%d'
    cmdpat += ' --meta_addrs=%s ' % metaseeds
    if args.small:
        cmdpat += ' --dbcfg=./template-small.cnf'
    shard_id = 'meta'
    pries = []
    secs = []
    i = 0
    if len(meta['nodes']):
        output_info(comf, "setup meta nodes ...")
    for item in metanodes:
        node = item['node']
        fname = item['file']
        idx = item['index']
        fullsync = item['fullsync']
        if 'fullsync_level' in meta and meta['fullsync_level'] != 1:
            vareles.append({"ip": node['ip'], 'port':node['port'],
            'variable_name':'fullsync_consistency_level',
            "type": "integer",
            'value':meta['fullsync_level']})
        setup_meta_env(node, machines, dirmap, commandslist, args)
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)
        targetdir='%s/%s/dba_tools' % (node['program_dir'], storagedir)
        node['nodemgr'] = nodemgrmaps.get(node['ip'])
        mach = machines.get(node['ip'])
        addNodeToFilesListMap(filesmap, node, reg_metaname, "%s/%s/scripts" % (node['program_dir'], serverdir))
        addNodeToFilesListMap(filesmap, node, fname, "%s/%s" % (targetdir, my_metaname))
        addNodeToFilesListMap(filesmap, node, xpanel_sqlfile, targetdir)
        cmd = cmdpat % (my_metaname, idx, cluster_name, shard_id, i+1, fullsync)
        if node.get('is_primary', False):
            pries.append([node['ip'], targetdir, cmd])
            vareles.append({"ip": node['ip'], 'port':node['port'],
                'variable_name':'ha_role', "type":"integer", 'value': 1})
        else:
            secs.append([node['ip'], targetdir, cmd])
        addToDirMap(dirmap, node['ip'], node['data_dir_path'])
        addToDirMap(dirmap, node['ip'], node['log_dir_path'])
        addToDirMap(dirmap, node['ip'], node['innodb_log_dir_path'])
        generate_storage_startstop(args, machines, node, i, filesmap)
        if args.autostart:
            generate_storage_service(args, machines, commandslist, node, i, filesmap)
        i+=1
    for item in pries:
        addToCommandsList(commandslist, item[0], item[1], item[2] + extraopt, "storage")
    for item in secs:
        addToCommandsList(commandslist, item[0], item[1], item[2] + extraopt, "storage")
    purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)

    # bootstrap the cluster
    if len(meta['nodes']) > 0:
        #firstmeta = meta['nodes'][0]
        firstmeta = None
        output_info(comf, "setup system tables ...")
        for node in meta['nodes']:
            if node.get('is_primary', False):
                firstmeta = node
                break
        targetdir='%s/%s/scripts' % (firstmeta['program_dir'], serverdir)
        cmdpat=r'python2 bootstrap.py --config=./%s --bootstrap_sql=./meta_inuse.sql' + extraopt
        addToCommandsList(commandslist, firstmeta['ip'], targetdir, cmdpat % reg_metaname, "computing")
        targetdir='%s/%s/dba_tools' % (firstmeta['program_dir'], storagedir)
        cmdpat=r'bash imysql.sh %s < %s'
        addToCommandsList(commandslist, firstmeta['ip'], targetdir, cmdpat % (str(firstmeta['port']), xpanel_sqlfile), "storage")
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)

    install_clusters(jscfg, machines, dirmap, filesmap, commandslist, reg_metaname, metaseeds, comf, metaobj, args)
    install_elasticsearch(jscfg, machines, metaseeds, comf, args)

    i = 0
    for node in clustermgr['nodes']:
        output_info(comf, "setup cluster_mgr on %s ..." % node['ip'])
        mach = machines.get(node['ip'])
        install_clustermgr_env(comf, mach, machines, args)
        setup_clustermgr_commands(args, i, machines, node, commandslist, dirmap, filesmap,
            metaseeds, initmember, node['ip'] not in nodemgrips)
        if args.autostart:
            generate_clustermgr_service(args, machines, commandslist, node, i, filesmap)
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)
        i += 1

    metajson = 'metadata.json'
    metaf = open('clustermgr/%s' % metajson, 'w')
    json.dump(metaobj, metaf, indent=4)
    metaf.close()

    worknode = None
    if len(meta['nodes']) > 0:
        worknode = meta['nodes'][0]
    elif len(nodemgr['nodes']) > 0:
        worknode = nodemgr['nodes'][0]
    elif len(clustermgr['nodes']) > 0:
        worknode = clustermgr['nodes'][0]

    if worknode is not None:
        output_info(comf, "update metadata from %s ..." % worknode['ip'])
        mach = machines.get(worknode['ip'])
        addNodeToFilesListMap(filesmap, worknode, 'modify_metadata.py', '.')
        addNodeToFilesListMap(filesmap, worknode, metajson, '.')
        addToCommandsList(commandslist, worknode['ip'], machines.get(worknode['ip'])['basedir'],
                "python2 modify_metadata.py --config %s --seeds=%s" % (metajson, metaseeds), "storage")
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)

    # start the nodemgr and clustermgr process finally.
    output_info(comf, "starting node_mgr nodes ...")
    for node in nodemgr['nodes']:
        if node['skip']:
            continue
        addToCommandsList(commandslist, node['ip'], ".", "bash start-nodemgr-%d.sh </dev/null >& run.log &" % node['brpc_http_port'])
    purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)
    output_info(comf, "starting cluster_mgr nodes ...")
    for node in clustermgr['nodes']:
        addToCommandsList(commandslist, node['ip'], "%s/bin" % clustermgrdir, "bash start_cluster_mgr.sh </dev/null >& start.log &")
    purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)

    # install xpanel
    install_xpanel(jscfg, machines, dirmap, filesmap, commandslist, metaseeds, comf, args)

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
    storagedirpfx = "kunlun-storage-"
    clustermgrdir = "kunlun-cluster-manager-%s" % args.product_version
    nodemgrdir = "kunlun-node-manager-%s" % args.product_version
    sudopfx=""
    if args.sudo:
        sudopfx="sudo "

    dirmap = {}
    filesmap = {}
    commandslist = []

    metaseeds = meta['group_seeds']

    nodemgrmaps = {}
    for node in nodemgr['nodes']:
        nodemgrmaps[node['ip']] = node

    # clean the nodemgr processes
    for node in nodemgr['nodes']:
        if node['skip']:
            continue
        mach = machines.get(node['ip'])
        output_info(comf, "Cleaning node_mgr and its managed instances on %s ..." % node['ip'])
        addToCommandsList(commandslist, node['ip'], "%s/bin" % nodemgrdir, "bash stop_node_mgr.sh")
        #for item in ["server_datadirs", "storage_datadirs", "storage_logdirs", "storage_waldirs"]:
        #    nodedirs = node[item].strip()
        #    for d in nodedirs.split(","):
        #        cmdpat = '%srm -fr %s/*'
        #        addToCommandsList(commandslist, node['ip'], "/", cmdpat % (sudopfx, d))
        addNodeToFilesListMap(filesmap, node, 'clear_instances.sh', '.')
        addNodeToFilesListMap(filesmap, node, 'clear_instance.sh', '.')
        addToCommandsList(commandslist, node['ip'], ".", 'bash ./clear_instances.sh %s %s >& clear.log || true' % (
            mach['basedir'], args.product_version))
        addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/instance_binaries' % mach['basedir'])
        addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/kunlun-node-manager*.service' % mach['basedir'])
        addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/setup_nodemgr*.sh' % mach['basedir'])
        addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/start-nodemgr*.sh' % mach['basedir'])
        addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/stop-nodemgr*.sh' % mach['basedir'])
        addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/kunlun_install*.log' % mach['basedir'])
        # meta related is also cleared here.
        addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/kunlun-storage*.service' % mach['basedir'])
        addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/start-storage*.sh' % mach['basedir'])
        addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/stop-storage*.sh' % mach['basedir'])
        addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/%s' % (mach['basedir'], nodemgrdir))
        for item in ["server_datadirs", "storage_datadirs", "storage_logdirs", "storage_waldirs"]:
            nodedirs = node[item].strip()
            for d in nodedirs.split(","):
                addToCommandsList(commandslist, node['ip'], ".", "rm -fr %s/*" % d)
        if args.setbashenv:
            addToCommandsList(commandslist, node['ip'], ".", "sed -i /KUNLUN_SET_ENV/d  ~/.bashrc")
        if args.autostart:
            servname = 'kunlun-node-manager-%d.service' % node['brpc_http_port']
            generate_systemctl_clean(servname, node['ip'], commandslist)
        if not args.cloud:
            addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/program_binaries' % mach['basedir'])
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)

    rnames = None
    if 'clusters' in jscfg and len(jscfg['clusters']) > 0:
        output_info(comf, "Cleaning all clusters specified in the configuration file ...")
        rnames = clean_clusters(args, jscfg['clusters'], nodemgrmaps, machines, comf)
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)
    clean_elasticsearch(jscfg, machines, metaseeds, comf, args)

    # clean the nodemgr processes
    for node in clustermgr['nodes']:
        mach = machines.get(node['ip'])
        output_info(comf, "Cleaning cluster_mgr on %s ..." % node['ip'])
        addToCommandsList(commandslist, node['ip'], "%s/bin" % clustermgrdir, "bash stop_cluster_mgr.sh")
        addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/instance_binaries' % mach['basedir'])
        addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/kunlun-cluster-manager*.service' % mach['basedir'])
        addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/setup_clustermgr*.sh' % mach['basedir'])
        addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/%s' % (mach['basedir'], clustermgrdir))
        if args.autostart:
            servname = 'kunlun-cluster-manager-%d.service' % node['brpc_raft_port']
            generate_systemctl_clean(servname, node['ip'], commandslist)
        if not args.cloud:
            addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/program_binaries' % mach['basedir'])
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)

    worknode = None
    if len(meta['nodes']) > 0:
        worknode = meta['nodes'][0]
    elif len(nodemgr['nodes']) > 0:
        worknode = nodemgr['nodes'][0]
    elif len(clustermgr['nodes']) > 0:
        worknode = clustermgr['nodes'][0]

    if worknode is not None:
        ip = worknode['ip']
        mach = machines.get(ip)
        if len(nodemgr['nodes']) > 0 and len(meta['nodes']) == 0 and 'group_seeds' in meta:
            metaobj = {}
            metaobj['node_manager'] = {'op':'remove', 'elements': nodemgr['nodes']}
            if rnames is not None and len(rnames) > 0:
                metaobj['delete_cluster'] = {'op':'remove', "elements": rnames}
            metajson = 'metadata.json'
            metaf = open('clustermgr/%s' % metajson, 'w')
            json.dump(metaobj, metaf, indent=4)
            metaf.close()
            addNodeToFilesListMap(filesmap, worknode, 'modify_metadata.py', '.')
            addNodeToFilesListMap(filesmap, worknode, metajson, '.')
            # Skip if we clean the meta.
            addToCommandsList(commandslist, ip, machines.get(worknode['ip'])['basedir'],
                "python2 modify_metadata.py --config %s --seeds=%s" % (metajson, metaseeds), "storage")
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)

    # clean the meta nodes
    for node in meta['nodes']:
        nodemgrobj = nodemgrmaps.get(node['ip'])
        if args.autostart:
            servname = 'kunlun-storage-%d.service' % node['port']
            generate_systemctl_clean(servname, node['ip'], commandslist)
        # skip it if it is processed by nodemgr clean routine.
        if not nodemgrobj['skip']:
            continue
        output_info(comf, "Cleaning meta node on %s ..." % node['ip'])
        targetdir='%s/%s/dba_tools' % (node['program_dir'], storagedir)
        cmdpat = r'bash stopmysql.sh %d'
        addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'], "storage")
        cmdpat = r'%srm -fr %s'
        addToCommandsList(commandslist, node['ip'], ".", cmdpat % (sudopfx, node['log_dir_path']))
        addToCommandsList(commandslist, node['ip'], ".", cmdpat % (sudopfx, node['data_dir_path']))
        addToCommandsList(commandslist, node['ip'], ".", cmdpat % (sudopfx, node['innodb_log_dir_path']))
        addToCommandsList(commandslist, node['ip'], ".", cmdpat % (sudopfx, node['program_dir']))
        addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/kunlun-storage*.service' % mach['basedir'])
        addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/start-storage*.sh' % mach['basedir'])
        addToCommandsList(commandslist, node['ip'], ".", 'rm -fr %s/stop-storage*.sh' % mach['basedir'])
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)

    # clean xpanel
    clean_xpanel(jscfg, machines, dirmap, filesmap, commandslist, comf, args)

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

    dirmap = {}
    filesmap = {}
    commandslist = []

    nodemgrmaps = {}
    for node in nodemgr['nodes']:
        nodemgrmaps[node['ip']] = node

    # stop the nodemgr processes
    for node in nodemgr['nodes']:
        if node['skip']:
            continue
        output_info(comf, "Stopping node_mgr and its managed instances on %s ..." % node['ip'])
        mach = machines.get(node['ip'])
        if args.autostart:
            servname = 'kunlun-node-manager-%d.service' % node['brpc_http_port']
            generate_systemctl_stop(servname, node['ip'], commandslist)
        else:
            addToCommandsList(commandslist, node['ip'], "%s/bin" % nodemgrdir, "bash stop_node_mgr.sh")
        addNodeToFilesListMap(filesmap, node, 'stop_instances.sh', '.')
        addToCommandsList(commandslist, node['ip'], ".", 'bash ./stop_instances.sh %s %s >& stop.log || true' % (
            mach['basedir'], args.product_version))
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)

    if 'clusters' in jscfg and len(jscfg['clusters']) > 0:
        output_info(comf, "Stopping all clusters specified in the configuration file ...")
        stop_clusters(jscfg['clusters'], nodemgrmaps, machines, comf, args)
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)
    stop_elasticsearch(jscfg, machines, comf, args)

    # stop the clustermgr processes
    for node in clustermgr['nodes']:
        output_info(comf, "Stopping cluster_mgr on %s ..." % node['ip'])
        if args.autostart:
            servname = 'kunlun-cluster-manager-%d.service' % node['brpc_raft_port']
            generate_systemctl_stop(servname, node['ip'], commandslist)
        else:
            addToCommandsList(commandslist, node['ip'], "%s/bin" % clustermgrdir, "bash stop_cluster_mgr.sh")
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)

    for node in meta['nodes']:
        nodemgrobj = nodemgrmaps.get(node['ip'])
        # skip it if it is processed by nodemgr clean routine.
        if not nodemgrobj['skip']:
            continue
        output_info(comf, "Stopping meta node on %s ..." % node['ip'])
        if args.autostart:
            servname = 'kunlun-storage-%d.service' % node['port']
            generate_systemctl_stop(servname, node['ip'], commandslist)
        else:
            targetdir='.'
            cmdpat = r'bash stop-storage-%d.sh'
            addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'], "storage")
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)

    # stop xpanel
    stop_xpanel(jscfg, machines, dirmap, filesmap, commandslist, comf, args)

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

    dirmap = {}
    filesmap = {}
    commandslist = []

    nodemgrmaps = {}
    for node in nodemgr['nodes']:
        nodemgrmaps[node['ip']] = node

    # start the nodemgr processes
    for node in nodemgr['nodes']:
        if node['skip']:
            continue
        output_info(comf, "Starting node_mgr on %s ..." % node['ip'])
        if args.autostart:
            servname = 'kunlun-node-manager-%d.service' % node['brpc_http_port']
            generate_systemctl_start(servname, node['ip'], commandslist)
        else:
            mach = machines.get(node['ip'])
            addNodeToFilesListMap(filesmap, node, 'start_instances.sh', '.')
            addToCommandsList(commandslist, node['ip'], ".", 'bash ./start_instances.sh %s %s >& start.log || true' % (
                mach['basedir'], args.product_version))
            addToCommandsList(commandslist, node['ip'], '.', "bash start-nodemgr-%d.sh </dev/null >& run.log &" % node['brpc_http_port'])
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)

    for node in meta['nodes']:
        nodemgrobj = nodemgrmaps.get(node['ip'])
        # skip it if it is processed by nodemgr clean routine.
        if not nodemgrobj['skip']:
            continue
        output_info(comf, "Starting meta node on %s ..." % node['ip'])
        if args.autostart:
            servname = 'kunlun-storage-%d.service' % node['port']
            generate_systemctl_start(servname, node['ip'], commandslist)
        else:
            cmdpat = r'bash start-storage-%d.sh'
            addToCommandsList(commandslist, node['ip'], '.', cmdpat % node['port'], "storage")
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)

    if 'clusters' in jscfg and len(jscfg['clusters']) > 0:
        output_info(comf, "Starting all clusters specified in the configuration file ...")
        start_clusters(jscfg['clusters'], nodemgrmaps, machines, comf, args)
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)
    start_elasticsearch(jscfg, machines, comf, args)

    # start the clustermgr processes
    for node in clustermgr['nodes']:
        output_info(comf, "Starting cluster_mgr on %s ..." % node['ip'])
        if args.autostart:
            servname = 'kunlun-cluster-manager-%d.service' % node['brpc_raft_port']
            generate_systemctl_start(servname, node['ip'], commandslist)
        else:
            addToCommandsList(commandslist, node['ip'], "%s/bin" % clustermgrdir, "bash start_cluster_mgr.sh")
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)

    # start xpanel
    start_xpanel(jscfg, machines, dirmap, filesmap, commandslist, comf, args)

def service_with_config(jscfg, comf, machines, args):
    meta = jscfg['meta']
    clustermgr = jscfg['cluster_manager']
    nodemgr = jscfg['node_manager']

    dirmap = {}
    filesmap = {}
    commandslist = []

    nodemgrmaps = {}
    for node in nodemgr['nodes']:
        nodemgrmaps[node['ip']] = node

    clustermgrips = set()
    for node in clustermgr['nodes']:
        clustermgrips.add(node['ip'])

    i = 0
    nodemgrips = set()
    for node in nodemgr['nodes']:
        nodemgrips.add(node['ip'])
        if node['skip']:
            continue
        output_info(comf, "Servicing node_mgr on %s ..." % node['ip'])
        generate_nodemgr_service(args, machines, commandslist, node, i, filesmap)
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)
        i += 1

    i = 0
    for node in meta['nodes']:
        node['nodemgr'] = nodemgrmaps.get(node['ip'])
        output_info(comf, "Servicing meta node on %s ..." % node['ip'])
        generate_storage_service(args, machines, commandslist, node, i, filesmap)
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)
        i+=1

    i = 0
    for node in clustermgr['nodes']:
        output_info(comf, "Servicing cluster_mgr on %s ..." % node['ip'])
        generate_clustermgr_service(args, machines, commandslist, node, i, filesmap)
        purge_cache_commands(args, comf, machines, dirmap, filesmap, commandslist)
        i += 1

def gen_cluster_config(args):
    if args.cluster_name == '':
        raise ValueError('Error: cluster_name must be provided')
    if args.outfile == '':
        raise ValueError('Error: outfile must be provided')
    jscfg = get_json_from_file(args.config)
    machines = {}
    setup_machines2(jscfg, machines, args)
    validate_and_set_config2(jscfg, machines, args)
    comf = open(r'clustermgr/%s' % args.outfile, 'w')
    resobj = {}
    resobj['machines'] = jscfg.get('machines',[])
    targetCluster = None
    for cluster in jscfg['clusters']:
        if cluster['name'] == args.cluster_name:
            targetCluster = cluster
    if targetCluster is None:
        raise Exception("Target cluster is not found")
    targetCluster['meta'] = jscfg['meta']
    targetCluster['clustermgr'] = jscfg['cluster_manager']
    resobj['cluster'] = targetCluster
    json.dump(resobj, comf, indent=4)
    comf.close()


# this should be put in contrib/common
def get_common_3rd_packages_filemap(args):
    return {
            "mysql-driver": ["mysql-connector-python-2.1.3.tar.gz", "mysql-connector-python-2.1.3"]
            }

# The original design is a 3-item list, [file-name, sub-dir, dir-after-extracted],
# but later decided to remove sub-dir to simplify code. So there will not be
# sub-dir unless it is really necessary.

# this should be put in contrib/x86_64
# If it is a gzip for docker image, the second item is the image name
# if it is a gzip for a directory, the second item is the dir after decompressed.
def get_x86_64_3rdpackages_filemap(args):
    return {
            "filebeat": ["filebeat-7.10.1-linux-x86_64.tar.gz", "filebeat-7.10.1-linux-x86_64"],
            "elasticsearch": ["elasticsearch-7.10.1.tar.gz", "elasticsearch:7.10.1"],
            "kibana": ["kibana-7.10.1.tar.gz", "kibana:7.10.1"],
            "haproxy": ["haproxy-2.5.0-bin.tar.gz", "haproxy-2.5.0-bin"],
            "jdk":["jdk-8u131-linux-x64.tar.gz", "jdk1.8.0_131"],
            "hadoop": ["hadoop-3.3.1.tar.gz", "hadoop-3.3.1"],
            "prometheus" : ["prometheus.tgz", "prometheus"]
            }

def get_arch_3rdpackages_filemap(args):
    arch = args.targetarch
    if arch == 'x86_64':
        return get_x86_64_3rdpackages_filemap(args)
    else: # not ready for aarch64 loongarch64, etc
        raise ValueError('bad arch: %s' % arch)

def get_3rdpackages_filemap(args):
    tmap = get_common_3rd_packages_filemap(args)
    tmap.update(get_arch_3rdpackages_filemap(args))
    return tmap

def download_packages(args):
    arch = args.targetarch
    prodver = args.product_version
    downtype = args.downloadtype
    contentTypes = set()
    downbase = get_downloadbase(args.downloadsite)
    targetdir="clustermgr"
    contentTypes.add('application/x-gzip')
    binarynames = ["kunlun-storage", "kunlun-server", "kunlun-cluster-manager", "kunlun-node-manager", "kunlun-proxysql"]
    xpanelname = "kunlun-xpanel"
    # download the binary packages
    for name in binarynames:
        fname = "%s-%s.tgz" % (name, prodver)
        if downtype == 'release':
            fpath = "releases_%s/%s/release-binaries/%s" % (arch, prodver, fname)
        elif downtype == 'daily_rel':
            fpath = "dailybuilds_%s/enterprise/%s" % (arch, fname)
        else:
            fpath = "dailybuilds_debug_%s/enterprise/%s" % (arch, fname)
        download_file(downbase, fpath, contentTypes, targetdir, args.overwrite, args)
    # download the xpanel docker image
    if downtype == 'release':
        fpath = 'releases_%s/%s/docker-allinone/kunlun-xpanel-%s.tar.gz' % (arch, prodver, prodver)
    else:
        fpath = 'dailybuilds_%s/docker-images/kunlun-xpanel-%s.tar.gz' % (arch, prodver)
    download_file(downbase, fpath, contentTypes, targetdir, args.overwrite, args)
    commap = get_common_3rd_packages_filemap(args)
    for pkgname in commap:
        finfo = commap[pkgname]
        fpath = 'contrib/common/%s' % finfo[0]
        download_file(downbase, fpath, contentTypes, targetdir, False, args)
    archmap = get_arch_3rdpackages_filemap(args)
    for pkgname in archmap:
        finfo = archmap[pkgname]
        fpath = 'contrib/%s/%s' % (arch, finfo[0])
        download_file(downbase, fpath, contentTypes, targetdir, args.overwrite, args)

if  __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Specify the arguments.')
    actions=["download", "install", "clean", "start", "stop", "service", "gen_cluster_config"]
    parser.add_argument('--config', type=str, help="The config path", default="config.json")
    parser.add_argument('--action', type=str, help="The action", default='install', choices=actions)
    parser.add_argument('--defuser', type=str, help="the default user", default=getpass.getuser())
    parser.add_argument('--defbase', type=str, help="the default basedir", default='/kunlun')
    parser.add_argument('--sudo', help="whether to use sudo", default=False, action='store_true')
    parser.add_argument('--verbose', help="verbose mode, to show more information", default=False, action='store_true')
    parser.add_argument('--product_version', type=str, help="kunlun version", default='1.2.1')
    parser.add_argument('--localip', type=str, help="The local ip address", default='127.0.0.1')
    parser.add_argument('--small', help="whether to use small template", default=False, action='store_true')
    parser.add_argument('--cloud', help="whether run on cloud images", default=False, action='store_true')
    parser.add_argument('--autostart', help="whether to start the cluster automaticlly", default=False, action='store_true')
    parser.add_argument('--setbashenv', help="whether to set the user bash env", default=False, action='store_true')
    parser.add_argument('--defbrpc_raft_port_clustermgr', type=int, help="default brpc_raft_port for cluster_manager", default=58001)
    parser.add_argument('--defbrpc_http_port_clustermgr', type=int, help="default brpc_http_port for cluster_manager", default=58000)
    parser.add_argument('--defpromethes_port_start_clustermgr', type=int, help="default prometheus starting port for cluster_manager", default=59010)
    parser.add_argument('--defbrpc_http_port_nodemgr', type=int, help="default brpc_http_port for node_manager", default=58002)
    parser.add_argument('--deftcp_port_nodemgr', type=int, help="default tcp_port for node_manager", default=58003)
    parser.add_argument('--defstorage_portrange_nodemgr', type=str, help="default port-range for storage nodes", default="57000-58000")
    parser.add_argument('--defserver_portrange_nodemgr', type=str, help="default port-range for server nodes", default="47000-48000")
    parser.add_argument('--defprometheus_port_start_nodemgr', type=int, help="default prometheus starting port for node_manager", default=58010)
    parser.add_argument('--outfile', type=str, help="the path for the cluster config", default="cluster.json")
    parser.add_argument('--cluster_name', type=str, help="the name of the cluster to generate the config file", default="")
    parser.add_argument('--download', help="whether to download before install operation", default=False, action='store_true')
    parser.add_argument('--downloadsite', type=str, help="the download base site", choices=['public', 'devsite', 'internal'], default='public')
    parser.add_argument('--downloadtype', type=str, help="the packages type", choices=['release', 'daily_rel', 'daily_debug'], default='release')
    parser.add_argument('--targetarch', type=str, help="the cpu arch for the packages to download/install", default=platform.machine())
    parser.add_argument('--overwrite', help="whether to overwrite existing file during download", default=False, action='store_true')
    parser.add_argument('--multipledc', help="whether used for installation in multiple datacenters", default=False, action='store_true')


    args = parser.parse_args()
    if not args.defbase.startswith('/'):
        raise ValueError('Error: the default basedir must be absolute path!')
    if args.autostart:
        args.sudo = True

    my_print(str(sys.argv))

    checkdirs(['clustermgr'])
    if args.action == 'download':
        download_packages(args)
    elif args.action == 'install':
        if args.download:
            download_packages(args)
        install_clustermgr(args)
    elif args.action == 'clean':
        clean_clustermgr(args)
    elif args.action == 'start':
        start_clustermgr(args)
    elif args.action == 'stop':
        stop_clustermgr(args)
    elif args.action == 'service':
        service_clustermgr(args)
    elif args.action == 'gen_cluster_config':
        gen_cluster_config(args)
    else:
        # just defensive, for more more actions later.
        pass
