#!/bin/python2
# Copyright (c) 2019 ZettaDB inc. All rights reserved.
# This source code is licensed under Apache 2.0 License,
# combined with Common Clause Condition 1.0, as detailed in the NOTICE file.

import sys
import json
import getpass
import uuid
import os
import argparse
from cluster_common import *

def validate_hamode(ha_mode):
    valids = ['mgr', 'rbr', 'no_rep']
    if ha_mode != '' and ha_mode not in valids:
        raise ValueError('Error: ha_mode must be empty or inside %s' % str(valids))

def get_hamode(shard):
    nodecnt = len(shard['nodes'])
    ha_mode = shard.get('ha_mode', '')
    if ha_mode != '':
        return ha_mode
    elif nodecnt == 1:
        return 'no_rep'
    else:
        return 'mgr'

def validate_config(jscfg, args):
    cluster = jscfg['cluster']
    datas = cluster['data']
    portmap = {}
    dirmap = {}

    i = 1
    for shard in datas:
        nodecnt = len(shard['nodes'])
        if nodecnt == 0:
            raise ValueError('Error: There must be at least one node in data shard%d' % i)
        ha_mode = shard.get('ha_mode', '')
        validate_hamode(ha_mode)
        if nodecnt == 1:
            if ha_mode != 'no_rep' and ha_mode != '':
                raise ValueError('Error: ha_mode is %s, but data shard%d has only one node' % (ha_mode, i))
        elif ha_mode == 'no_rep':
            raise ValueError('Error: ha_mode is %s, but data shard%d has two or more nodes' % (ha_mode, i))
        hasPrimary=False
        for node in shard['nodes']:
            addPortToMachine(portmap, node['ip'], node['port'])
            if 'xport' in node:
                addPortToMachine(portmap, node['ip'], node['xport'])
            if 'mgr_port' in node:
                addPortToMachine(portmap, node['ip'], node['mgr_port'])
            addDirToMachine(dirmap, node['ip'], node['data_dir_path'])
            addDirToMachine(dirmap, node['ip'], node['log_dir_path'])
            if 'innodb_log_dir_path' in node:
                addDirToMachine(dirmap, node['ip'], node['innodb_log_dir_path'])
            if node.get('is_primary', False):
                if hasPrimary:
                    raise ValueError('Error: Two primaries found in shard%d, there should be one and only one Primary specified !' % i)
                else:
                    hasPrimary = True
        if nodecnt > 1:
            if not hasPrimary:
                raise ValueError('Error: No primary found in shard%d, there should be one and only one primary specified !' % i)
        else:
            node['is_primary'] = True
        i+=1


def generate_install_scripts(jscfg, args):
    validate_config(jscfg, args)

    installtype = args.installtype
    localip = '127.0.0.1'

    machines = {}
    for mach in jscfg['machines']:
        ip=mach['ip']
        user=mach.get('user', args.defuser)
        base=mach.get('basedir', args.defbase)
        addMachineToMap(machines, ip, user, base)

    storagedir = "kunlun-storage-%s" % args.product_version

    valgrindopt = ""
    if args.valgrind:
        valgrindopt = "--valgrind"

    filesmap = {}
    commandslist = []
    dirmap = {}

    cluster = jscfg['cluster']
    cluster_name = cluster.get('name', 'individual_shards')
    datas = cluster['data']

    cmdpat = 'python2 install-mysql.py --config=./%s --target_node_index=%d --cluster_id=%s --shard_id=%s --ha_mode=%s --server_id=%d'
    if args.small:
        cmdpat += ' --dbcfg=./template-small.cnf'
    # commands like:
    # python2 install-mysql.py --config=./mysql_meta.json --target_node_index=0 --server_id=[int]
    targetdir='%s/dba_tools' % storagedir
    pries = []
    secs = []

    i=1
    for shard in datas:
        if not 'group_uuid' in shard:
            shard['group_uuid'] = getuuid()
        shard_id = shard.get('name', '')
        if shard_id == '':
            shard_id = "shard%d" % i
        my_shardname = "mysql_shard%d.json" % i
        shardf = open(r'install/%s' % my_shardname, 'w')
        json.dump(shard, shardf, indent=4)
        shardf.close()
        ha_mode = get_hamode(shard)
        j = 0
        for node in shard['nodes']:
            addNodeToFilesMap(filesmap, node, my_shardname, targetdir)
            addIpToMachineMap(machines, node['ip'], args)
            cmd = cmdpat % (my_shardname, j, cluster_name, shard_id, ha_mode, j+1)
            if node.get('is_primary', False):
                pries.append([node['ip'], targetdir, cmd])
            else:
                secs.append([node['ip'], targetdir, cmd])
            addToDirMap(dirmap, node['ip'], node['data_dir_path'])
            addToDirMap(dirmap, node['ip'], node['log_dir_path'])
            if 'innodb_log_dir_path' in node:
                addToDirMap(dirmap, node['ip'], node['innodb_log_dir_path'])
            j += 1
        i+=1
    for item in pries:
        addToCommandsList(commandslist, item[0], item[1], item[2])
    for item in secs:
        addToCommandsList(commandslist, item[0], item[1], item[2])

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
            process_command_noenv(comf, args, machines, ip, mach['basedir'], 'tar -xzf %s.tgz' % storagedir)

	# files
        flist = [
                    ['build_driver_formysql.sh', '%s/resources' % storagedir],
                    ['process_deps.sh', '.']
                ]
        for fpair in flist:
            process_file(comf, args, machines, ip, 'install/%s' % fpair[0], "%s/%s" % (mach['basedir'], fpair[1]))

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
            process_file(comf, args, machines, ip, 'install/%s' % fname, '%s/%s' % (mach['basedir'], fmap[fname]))

    # The reason for not using commands map is that, we need to keep the order for the commands.
    process_commandslist_setenv(comf, args, machines, commandslist)
    comf.close()

# The order is meta shard -> data shards -> cluster_mgr -> comp nodes
def generate_start_scripts(jscfg, args):
    localip = '127.0.0.1'

    machines = {}
    for mach in jscfg['machines']:
        ip=mach['ip']
        user=mach.get('user', args.defuser)
        base=mach.get('basedir', args.defbase)
        addMachineToMap(machines, ip, user, base)

    storagedir = "kunlun-storage-%s" % args.product_version

    valgrindopt = ""
    if args.valgrind:
        valgrindopt = "--valgrind"

    filesmap = {}
    commandslist = []
    
    cluster = jscfg['cluster']
    # commands like:
    # bash startmysql.sh [port]
    targetdir='%s/dba_tools' % storagedir
    datas = cluster['data']
    for shard in datas:
        for node in shard['nodes']:
            addIpToMachineMap(machines, node['ip'], args)
            cmdpat = r'bash startmysql.sh %s'
            addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'])
    
    com_name = 'commands.sh'
    os.system('mkdir -p start')
    comf = open(r'start/%s' % com_name, 'w')
    comf.write('#! /bin/bash\n')
    process_commandslist_setenv(comf, args, machines, commandslist)
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

    commandslist = []
    cluster = jscfg['cluster']

    # bash stopmysql.sh [port]
    targetdir='%s/dba_tools' % storagedir
    datas = cluster['data']
    for shard in datas:
        for node in shard['nodes']:
            addIpToMachineMap(machines, node['ip'], args)
            cmdpat = r'bash stopmysql.sh %d'
            addToCommandsList(commandslist, node['ip'], targetdir, cmdpat % node['port'], "storage")

    com_name = 'commands.sh'
    os.system('mkdir -p stop')
    comf = open(r'stop/%s' % com_name, 'w')
    comf.write('#! /bin/bash\n')
    process_commandslist_setenv(comf, args, machines, commandslist)
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

    env_cmdlist = []
    noenv_cmdlist = []
    cluster = jscfg['cluster']

    # bash stopmysql.sh [port]
    targetdir='%s/dba_tools' % storagedir
    datas = cluster['data']
    for shard in datas:
        for node in shard['nodes']:
            addIpToMachineMap(machines, node['ip'], args)
            cmdpat = r'bash stopmysql.sh %d'
            addToCommandsList(env_cmdlist, node['ip'], targetdir, cmdpat % node['port'], "storage")
            cmdpat = r'%srm -fr %s'
            addToCommandsList(noenv_cmdlist, node['ip'], ".", cmdpat % (sudopfx, node['log_dir_path']))
            addToCommandsList(noenv_cmdlist, node['ip'], ".", cmdpat % (sudopfx, node['data_dir_path']))
            if 'innodb_log_dir_path' in node:
                addToCommandsList(noenv_cmdlist, node['ip'], ".", cmdpat % (sudopfx, node['innodb_log_dir_path']))

    if cleantype == 'full':
        for ip in machines:
            mach =machines[ip]
            cmdpat = '%srm -fr %s/*'
            addToCommandsList(noenv_cmdlist, ip, ".", cmdpat % (sudopfx, mach['basedir']))

    com_name = 'commands.sh'
    os.system('mkdir -p clean')
    comf = open(r'clean/%s' % com_name, 'w')
    comf.write('#! /bin/bash\n')
    process_commandslist_setenv(comf, args, machines, env_cmdlist)
    process_commandslist_noenv(comf, args, machines, noenv_cmdlist)
    comf.close()

if  __name__ == '__main__':
    actions=["install", "start", "stop", "clean"]
    parser = argparse.ArgumentParser(description='Specify the arguments.')
    parser.add_argument('--action', type=str, help="The action", required=True, choices=actions)
    parser.add_argument('--config', type=str, help="The cluster config path", required=True)
    parser.add_argument('--defuser', type=str, help="the default user", default=getpass.getuser())
    parser.add_argument('--defbase', type=str, help="the default basedir", default='/kunlun')
    parser.add_argument('--installtype', type=str, help="the install type", default='full', choices=['full', 'cluster'])
    parser.add_argument('--cleantype', type=str, help="the clean type", default='full', choices=['full', 'cluster'])
    parser.add_argument('--sudo', help="whether to use sudo", default=False, action='store_true')
    parser.add_argument('--small', help="whether to use small template", default=False, action='store_true')
    parser.add_argument('--localip', type=str, help="The local ip address", default=gethostip())
    parser.add_argument('--product_version', type=str, help="kunlun version", default='1.0.1')
    parser.add_argument('--valgrind', help="whether to use valgrind", default=False, action='store_true')

    args = parser.parse_args()
    checkdirs(actions)

    my_print(str(sys.argv))
    jscfg = get_json_from_file(args.config)

    if args.action == 'install':
        generate_install_scripts(jscfg, args)
    elif args.action == 'start':
        generate_start_scripts(jscfg, args)
    elif args.action == 'stop':
        generate_stop_scripts(jscfg, args)
    elif args.action == 'clean':
        generate_clean_scripts(jscfg, args)
    else:
        usage()
        sys.exit(1)
