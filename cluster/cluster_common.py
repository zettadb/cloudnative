import sys
import json
import collections
import os
import os.path
import socket
import uuid
import getpass

def my_print(toprint):
    if sys.version_info.major == 2:
        sys.stdout.write(toprint + "\n")
    else:
        print(toprint)

def run_command_verbose(command, dryrun):
    my_print(command)
    sys.stdout.flush()
    if not dryrun:
        os.system(command)
        sys.stdout.flush()

def run_remote_command(machines, ip, progdir, targetdir, command, dryrun):
    mach = machines.get(ip)
    sshport = mach.get('sshport', 22)
    if progdir.startswith('/'):
        realdir = progdir
    else:
        realdir = "%s/%s" % (mach['basedir'], progdir)
    if targetdir.startswith('/'):
        workdir = targetdir
    else:
        workdir = "%s/%s" % (realdir, targetdir)
    envstr = "export PATH=%s/bin:$PATH; export LD_LIBRARY_PATH=%s/lib:%s/lib64:$LD_LIBRARY_PATH" % (realdir, realdir, realdir)
    cmdstr='''bash remote_run.sh --sshport=%d --user=%s %s '%s; cd %s || exit 1; %s' '''
    tup= (sshport, mach['user'], ip, envstr, workdir, command)
    run_command_verbose(cmdstr % tup, dryrun)

def stop_clustermgr_node(machines, progdir, node, dryrun):
    command = "bash stop_cluster_mgr.sh"
    run_remote_command(machines, node['ip'], progdir, 'bin', command, dryrun)

def stop_clustermgr_node_usingidx(machines, progdir, clustermgrobj, idx, dryrun):
    node = clustermgrobj['nodes'][idx]
    stop_clustermgr_node(machines, progdir, node, dryrun)

def start_clustermgr_node(machines, progdir, node, dryrun):
    command = "bash start_cluster_mgr.sh >& run.log"
    run_remote_command(machines, node['ip'], progdir, 'bin', command, dryrun)

def start_clustermgr_node_usingidx(machines, progdir, clustermgrobj, idx, dryrun):
    node = clustermgrobj['nodes'][idx]
    start_clustermgr_node(machines, progdir, node, dryrun)

def stop_nodemgr_node(machines, progdir, node, dryrun):
    command = "bash stop_node_mgr.sh"
    run_remote_command(machines, node['ip'], progdir, 'bin', command, dryrun)

def stop_nodemgr_node_usingidx(machines, progdir, nodemgrobj, idx, dryrun):
    node = nodemgrobj['nodes'][idx]
    stop_nodemgr_node(machines, progdir, node, dryrun)

def start_nodemgr_node(machines, progdir, node, dryrun):
    command = "bash start_node_mgr.sh >& run.log"
    run_remote_command(machines, node['ip'], progdir, 'bin', command, dryrun)

def start_nodemgr_node_usingidx(machines, progdir, nodemgrobj, idx, dryrun):
    node = nodemgrobj['nodes'][idx]
    start_nodemgr_node(machines, progdir, node, dryrun)

def start_storage_node(machines, progdir, node, dryrun):
    command = "bash startmysql.sh %s" % str(node['port'])
    run_remote_command(machines, node['ip'], progdir, 'dba_tools', command, dryrun)

def start_storage_node_usingidx(machines, progdir, groupobj, idx, dryrun):
    node = groupobj['nodes'][idx]
    start_storage_node(machines, progdir, node, dryrun)

def stop_storage_node(machines, progdir, node, dryrun):
    command = "bash stopmysql.sh %s" % str(node['port'])
    run_remote_command(machines, node['ip'], progdir, 'dba_tools', command, dryrun)

def stop_storage_node_usingidx(machines, progdir, groupobj, idx, dryrun):
    node = groupobj['nodes'][idx]
    stop_storage_node(machines, progdir, node, dryrun)

def kill_storage_node(machines, progdir, node, dryrun):
    command = "bash killmysql.sh %s" % str(node['port'])
    run_remote_command(machines, node['ip'], progdir, 'dba_tools', command, dryrun)

def kill_storage_node_usingidx(machines, progdir, groupobj, idx, dryrun):
    node = groupobj['nodes'][idx]
    kill_storage_node(machines, progdir, node, dryrun)

def start_server_node(machines, progdir, node, dryrun):
    command = "python2 start_pg.py --port=%s" % str(node['port'])
    run_remote_command(machines, node['ip'], progdir, 'scripts', command, dryrun)

def start_server_node_usingidx(machines, progdir, compobj, idx, dryrun):
    node = compobj['nodes'][idx]
    start_server_node(machines, progdir, node, dryrun)

def stop_server_node(machines, progdir, node, dryrun):
    command = "pg_ctl -D %s stop -m immediate" % str(node['datadir'])
    run_remote_command(machines, node['ip'], progdir, 'scripts', command, dryrun)

def stop_server_node_usingidx(machines, progdir, compobj, idx, dryrun):
    node = compobj['nodes'][idx]
    stop_server_node(machines, progdir, node, dryrun)

def addIpToMachineMap(map, ip, args, haspg=False):
    #my_print("add ip %s" % ip)
    if not ip in map:
        mac={"ip":ip, "user":args.defuser, "basedir":args.defbase, "haspg":haspg}
        map[ip] = mac

def generate_haproxy_config(cluster, machines, subdir, confname):
    comps = cluster['comp']['nodes']
    haproxy = cluster['haproxy']
    mach = machines[haproxy['ip']]
    maxconn = haproxy.get('maxconn', 900)
    conf = open("%s/%s" % (subdir, confname), 'w')
    conf.write('''# generated automatically
    global
        pidfile %s/haproxy-%d.pid
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
''' % (mach['basedir'], haproxy['port'], maxconn, haproxy['port']))
    i = 1
    for node in comps:
        conf.write("        server comp%d %s:%d weight 1 check inter 10s\n" % (i, node['ip'], node['port']))
        i += 1
    conf.close()

def get_json_from_file(filepath):
    jsconf = open(filepath)
    jstr = jsconf.read()
    jscfg = json.loads(jstr, object_pairs_hook=collections.OrderedDict)
    jsconf.close()
    return jscfg

def addMachineToMap(map, ip, user, basedir, haspg=False):
    # We can add logic here to check if the item exsits, new added should be unique to existing.
    if ip in map:
        return
    mac={"ip":ip, "user":user, "basedir":basedir, "haspg": haspg}
    map[ip] = mac

def gethostip():
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    return ip

def getuuid():
    return str(uuid.uuid1())

def addIpToFilesMap(map, ip, fname, targetdir):
    if not ip in map:
        map[ip] = {}
    tmap = map[ip]
    if not fname in tmap:
        tmap[fname] = targetdir

def addNodeToFilesMap(map, node, fname, targetdir):
    ip = node['ip']
    addIpToFilesMap(map, ip, fname, targetdir)

def addIpToFilesListMap(map, ip, fname, targetdir):
    if not ip in map:
        map[ip] = []
    tlist = map[ip]
    tlist.append([fname, targetdir])

def addNodeToFilesListMap(map, node, fname, targetdir):
    ip = node['ip']
    addIpToFilesListMap(map, ip, fname, targetdir)

def addNodeToIpset(set, node):
    ip = node['ip']
    set.add(ip)

# Not used currently.
def addToCommandsMap(map, ip, targetdir, command):
    if not ip in map:
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
    if not ip in map:
        map[ip] = []
    dirs = map[ip]
    dirs.append(newdir)

def islocal(args, ip, user):
    if ip.startswith("127") or ip in [args.localip, "localhost", socket.gethostname()]:
        if getpass.getuser() == user:
            return True
    return False

def process_filelist(comf, args, machines, filelist):
    for filetup in filelist:
        ip = filetup[0]
        mach = machines[ip]
        sshport = mach.get('sshport', 22)
        if islocal(args, ip, mach['user']):
            # For local, we do not consider the user.
            mkstr = '''/bin/bash -xc $"cp -f %s %s" >& lastlog '''
            tup= (filetup[1], filetup[2])
        else:
            mkstr = '''bash dist.sh --sshport=%d --hosts=%s --user=%s %s %s >& lastlog '''
            tup= (sshport, ip, mach['user'], filetup[1], filetup[2])
        comf.write(mkstr % tup)
        comf.write("\n")

def process_file(comf, args, machines, ip, source, target):
    process_filelist(comf, args, machines, [[ip, source, target]])

def process_commandslist_noenv(comf, args, machines, commandslist):
    for cmd in commandslist:
        ip=cmd[0]
        mach = machines[ip]
        sshport = mach.get('sshport', 22)
        if islocal(args, ip, mach['user']):
            # For local, we do not consider the user.
            mkstr = '''/bin/bash -xc $"cd %s || exit 1; %s" >& lastlog '''
            tup= (cmd[1], cmd[2])
        else:
            ttyopt=""
            if cmd[2].find("sudo ") >= 0:
                ttyopt="--tty"
            mkstr = '''bash remote_run.sh --sshport=%d %s --user=%s %s $"cd %s || exit 1; %s" >& lastlog '''
            tup= (sshport, ttyopt, mach['user'], ip, cmd[1], cmd[2])
        comf.write(mkstr % tup)
        comf.write("\n")

def process_command_noenv(comf, args, machines, ip, targetdir, command):
    process_commandslist_noenv(comf, args, machines, [[ip, targetdir, command]])

def process_commandslist_setenv(comf, args, machines, commandslist):
    for cmd in commandslist:
        ip=cmd[0]
        mach = machines[ip]
        sshport = mach.get('sshport', 22)
        if islocal(args, ip, mach['user']):
            # For local, we do not consider the user.
            mkstr = '''/bin/bash -c $"cd %s && cd %s || exit 1; envtype=%s && source %s/env.sh; %s" >& lastlog '''
            tup= (mach['basedir'], cmd[1], cmd[3], mach['basedir'], cmd[2])
        else:
            ttyopt=""
            if cmd[2].find("sudo ") >= 0:
                ttyopt="--tty"
            mkstr = '''bash remote_run.sh --sshport=%d %s --user=%s %s $"cd %s && cd %s || exit 1; envtype=%s && source %s/env.sh; %s" >& lastlog '''
            tup= (sshport, ttyopt, mach['user'], ip, mach['basedir'], cmd[1], cmd[3], mach['basedir'], cmd[2])
        comf.write(mkstr % tup)
        comf.write("\n")

def process_command_setenv(comf, args, machines, ip, targetdir, command, envtype='no'):
    process_commandslist_setenv(comf, args, machines, [[ip, targetdir, command, envtype]])

def process_dirmap(comf, dirmap, machines, args):
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

def process_fileslistmap(comf, filesmap, machines, prefix, args):
    # files copy.
    for ip in filesmap:
        mach = machines.get(ip)
        fmap = filesmap[ip]
        for fpair in fmap:
            process_file(comf, args, machines, ip, '%s/%s' % (prefix, fpair[0]), '%s/%s' % (mach['basedir'], fpair[1]))

def process_filesmap(comf, filesmap, machines, prefix, args):
    # files copy.
    for ip in filesmap:
        mach = machines.get(ip)
        fmap = filesmap[ip]
        for fname in fmap:
            process_file(comf, args, machines, ip, '%s/%s' % (prefix, fname), '%s/%s' % (mach['basedir'], fmap[fname]))

def validate_ha_mode(ha_mode):
    if ha_mode not in ['rbr', 'no_rep', 'mgr']:
        raise ValueError('Error: The ha_mode must be rbr, mgr or no_rep')

def checkdirs(dirs):
    for d in dirs:
        if not os.path.exists(d):
            os.mkdir(d)

def addPortToMachine(map, ip, port):
    if not ip in map:
        map[ip] = set([port])
    else:
        pset = map[ip]
        if port in pset:
            raise ValueError("duplicate port:%s on host:%s" % (str(port), ip))
        else:
            pset.add(port)

def addDirToMachine(map, ip, directory):
    if not ip in map:
        map[ip] = set([directory])
    else:
        dset = map[ip]
        if directory in dset:
            raise ValueError("duplicate directory:%s on host:%s" % (directory, ip))
        else:
            dset.add(directory)

# Setup the machines object for one-key installation script(binary version)
def setup_machines1(jscfg, machines, args):
    machnodes = jscfg.get('machines', [])
    cluster = jscfg['cluster']
    meta = cluster['meta']
    datas = cluster['data']
    comp = cluster['comp']
    clustermgr = cluster['clustermgr']
    for mach in machnodes:
        ip=mach['ip']
        user=mach.get('user', args.defuser)
        base=mach.get('basedir', args.defbase)
        addMachineToMap(machines, ip, user, base)
    for node in meta['nodes']:
        addIpToMachineMap(machines, node['ip'], args)
    for shard in datas:
        for node in shard['nodes']:
            addIpToMachineMap(machines, node['ip'], args)
    for node in comp['nodes']:
        addIpToMachineMap(machines, node['ip'], args, True)
    if 'ip' in clustermgr:
        addIpToMachineMap(machines, clustermgr['ip'], args)
    elif 'nodes' in clustermgr:
        for node in clustermgr['nodes']:
            addIpToMachineMap(machines, node['ip'], args)
    haproxy = cluster.get("haproxy", None)
    if haproxy is not None:
        addIpToMachineMap(machines, haproxy['ip'], args)

# ha_mode logic:
# for meta_ha_mode, the check order is: meta['ha_mode'] -> cluster['ha_mode'] -> no_rep(1 node)/mgr(multi nodes)
# for shard_ha_mode, the check order is: cluster['ha_mode'] -> meta_ha_mode
# This validates and sets the config object for one-key installation script(binary version)
def validate_and_set_config1(jscfg, machines, args):
    cluster = jscfg['cluster']
    meta = cluster['meta']
    comps = cluster['comp']['nodes']
    datas = cluster['data']
    clustermgr = cluster['clustermgr']
    haproxy = cluster.get("haproxy", None)
    portmap = {}
    dirmap = {}

    meta_ha_mode = ''
    shard_ha_mode = ''
    if 'ha_mode' in cluster:
        mode = cluster['ha_mode']
        validate_ha_mode(mode)
        meta_ha_mode = mode
        shard_ha_mode = mode

    if 'ha_mode' in meta:
        mode = meta.get('ha_mode')
        validate_ha_mode(mode)
        meta_ha_mode = mode

    metacnt = len(meta['nodes'])
    if metacnt == 0:
        raise ValueError('Error: There must be at least one node in meta shard')
    if meta_ha_mode == '':
        if metacnt > 1:
            meta_ha_mode = 'mgr'
        else:
            meta_ha_mode = 'no_rep'

    meta['ha_mode'] = meta_ha_mode
    if metacnt > 1 and meta_ha_mode == 'no_rep':
        raise ValueError('Error: meta_ha_mode is no_rep, but there are multiple nodes in meta shard')
    elif metacnt == 1 and meta_ha_mode != 'no_rep':
        raise ValueError('Error: meta_ha_mode is mgr/rbr, but there is only one node in meta shard')

    hasPrimary=False
    for node in meta['nodes']:
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
                raise ValueError('Error: Two primaries found in meta shard, there should be one and only one Primary specified !')
            else:
                hasPrimary = True
    if metacnt > 1:
        if not hasPrimary:
            raise ValueError('Error: No primary found in meta shard, there should be one and only one primary specified !')
    else:
        node['is_primary'] = True

    for node in comps:
        mach = machines.get(node['ip'])
        mach['haspg'] = True
        addPortToMachine(portmap, node['ip'], node['port'])
        addPortToMachine(portmap, node['ip'], node['mysql_port'])
        addDirToMachine(dirmap, node['ip'], node['datadir'])

    if haproxy is not None:
        addPortToMachine(portmap, haproxy['ip'], haproxy['port'])
        if 'mysql_port' in haproxy:
            addPortToMachine(portmap, haproxy['ip'], haproxy['mysql_port'])

    if shard_ha_mode == '':
        shard_ha_mode = meta_ha_mode
    cluster['ha_mode'] = shard_ha_mode

    i=1
    for shard in datas:
        nodecnt = len(shard['nodes'])
        if nodecnt == 0:
            raise ValueError('Error: There must be at least one node in data shard%d' % i)
        if nodecnt > 1 and shard_ha_mode == 'no_rep':
            raise ValueError('Error: shard_ha_mode is no_rep, but data shard%d has two or more' % i)
        elif nodecnt == 1 and shard_ha_mode != 'no_rep':
            raise ValueError('Error: shard_ha_mode is mgr/rbr, but data shard%d has only one' % i)
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
    
    if 'ip' in clustermgr and 'nodes' in clustermgr:
        raise ValueError('Error: ip or nodes can not be both set for clustermgr !')
    elif 'ip' in clustermgr:
        node = {"ip": clustermgr['ip']}
        del clustermgr['ip']
        if 'brpc_raft_port' in clustermgr:
            node['brpc_raft_port'] = clsutermgr['brpc_raft_port']
            del clsutermgr['brpc_raft_port']
        else:
            node['brpc_raft_port'] = args.defbrpc_raft_port
        addPortToMachine(portmap, node['ip'], node['brpc_raft_port'])
        if 'brpc_http_port' in clustermgr:
            node['brpc_http_port'] = clsutermgr['brpc_http_port']
            del clsutermgr['brpc_http_port']
        else:
            node['brpc_http_port'] = args.defbrpc_http_port
        addPortToMachine(portmap, node['ip'], node['brpc_http_port'])
        clustermgr['nodes'] = [node]
    elif 'nodes' in clustermgr:
        for node in clustermgr['nodes']:
            if 'brpc_raft_port' in node:
                addPortToMachine(portmap, node['ip'], node['brpc_raft_port'])
            else:
                node['brpc_raft_port'] = args.defbrpc_raft_port
                addPortToMachine(portmap, node['ip'], args.defbrpc_raft_port)
            if 'brpc_http_port' in node:
                addPortToMachine(portmap, node['ip'], node['brpc_http_port'])
            else:
                node['brpc_http_port'] = args.defbrpc_http_port
                addPortToMachine(portmap, node['ip'], args.defbrpc_http_port)
    else:
        raise ValueError('Error:ip or(x-or) nodes must be set for clustermgr !')

# Setup the machines object for clustermgr initialization/destroy scripts.
def setup_machines2(jscfg, machines, args):
    machnodes = jscfg.get('machines', [])
    meta = jscfg['meta']
    metanodes = meta.get('nodes', [])
    nodemgr = jscfg.get('node_manager', {"nodes": []})
    nodemgrnodes = nodemgr.get('nodes', [])
    clustermgr = jscfg.get('cluster_manager', {"nodes": []})
    clustermgrnodes = clustermgr.get('nodes', [])
    clusters = jscfg.get('clusters', [])
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
    if 'xpanel' in jscfg:
        addIpToMachineMap(machines, jscfg['xpanel']['ip'], args)
    for cluster in clusters:
        for node in cluster['comp']['nodes']:
            addIpToMachineMap(machines, node['ip'], args, True)
        for shard in cluster['data']:
            for node in shard['nodes']:
                addIpToMachineMap(machines, node['ip'], args)
        if 'haproxy' in cluster:
            node = cluster['haproxy']
            addIpToMachineMap(machines, node['ip'], args)

def set_storage_using_nodemgr(machines, item, noden, innodb_buf="1024MB"):
    if 'data_dir_path' not in item:
        item['data_dir_path'] = "%s/%s" % (noden['storage_datadirs'].split(",")[0], str(item['port']))
    if 'log_dir_path' not in item:
        item['log_dir_path'] = "%s/%s" % (noden['storage_logdirs'].split(",")[0], str(item['port']))
    if 'innodb_log_dir_path' not in item:
        item['innodb_log_dir_path'] = "%s/%s" % (noden['storage_waldirs'].split(",")[0], str(item['port']))
    mach = machines.get(item['ip'])
    item['program_dir'] = "instance_binaries/storage/%s" % str(item['port'])
    item['user'] = mach['user']
    if 'innodb_buffer_pool_size' not in item:
        item['innodb_buffer_pool_size'] = innodb_buf

def set_server_using_nodemgr(machines, item, noden):
    if 'datadir' not in item:
        item['datadir'] = "%s/%s" % (noden['server_datadirs'].split(",")[0], str(item['port']))
    item['program_dir'] = "instance_binaries/computer/%s" % str(item['port'])

# validate and set the configuration object for clustermgr initialization/destroy scripts.
def validate_and_set_config2(jscfg, machines, args):
    meta = jscfg.get('meta', {'nodes':[]})
    if not 'nodes' in meta:
        meta['nodes'] = []
    clustermgr = jscfg.get('cluster_manager', {'nodes':[]})
    if not 'nodes' in clustermgr:
        clustermgr['nodes'] = []
    if not 'cluster_manager' in clustermgr:
        jscfg['cluster_manager'] = clustermgr
    nodemgr = jscfg.get('node_manager', {'nodes':[]})
    if not 'nodes' in nodemgr:
        nodemgr['nodes'] = []
    if not 'node_manager' in nodemgr:
        jscfg['node_manager'] = nodemgr
    clusters = jscfg.get('clusters', [])
    if not 'clusters' in jscfg:
        jscfg['clusters'] = clusters

    portmap = {}
    dirmap = {}

    clustermgrips = set()
    for node in clustermgr['nodes']:
        if node['ip'] in clustermgrips:
            raise ValueError('Error: %s exists, only one cluster_mgr can be run on a machine!' % node['ip'])
        if 'valgrind' not in node:
            node['valgrind'] = False
        clustermgrips.add(node['ip'])
        if 'brpc_raft_port' in node:
            addPortToMachine(portmap, node['ip'], node['brpc_raft_port'])
        else:
            node['brpc_raft_port'] = args.defbrpc_raft_port_clustermgr
            addPortToMachine(portmap, node['ip'], args.defbrpc_raft_port_clustermgr)
        if 'brpc_http_port' in node:
            addPortToMachine(portmap, node['ip'], node['brpc_http_port'])
        else:
            node['brpc_http_port'] = args.defbrpc_http_port_clustermgr
            addPortToMachine(portmap, node['ip'], args.defbrpc_http_port_clustermgr)
        if 'prometheus_port_start' in node:
            addPortToMachine(portmap, node['ip'], node['prometheus_port_start'])
        else:
            node['prometheus_port_start'] = args.defpromethes_port_start_clustermgr
            addPortToMachine(portmap, node['ip'], node['prometheus_port_start'])

    defpaths = {
            "server_datadirs": "server_datadir",
            "storage_datadirs": "storage_datadir",
            "storage_logdirs": "storage_logdir",
            "storage_waldirs": "storage_waldir",
        }
    nodemgrips = set()
    nodemgrmaps = {}
    for node in nodemgr['nodes']:
        node['storage_usedports'] = []
        node['server_usedports'] = []
        if 'nodetype' not in node:
            node['nodetype'] = 'both'
        if 'valgrind' not in node:
            node['valgrind'] = False
        if 'skip' not in node:
            node['skip'] = False
        if 'nodetype' not in node:
            node['nodetype'] = 'none'
        # default 8 cpus
        if 'total_cpu_cores' not in node:
            node['total_cpu_cores'] = 8
        # default 16GB memory.
        if 'total_mem' not in node:
            node['total_mem'] = 16384
        if 'storage_portrange' not in node:
            node['storage_portrange'] = args.defstorage_portrange_nodemgr
        if 'server_portrange' not in node:
            node['server_portrange'] = args.defserver_portrange_nodemgr
        # validate other configurations
        if 'storage_curport' not in node:
            range1 = node['storage_portrange'].split('-')
            node['storage_curport'] = int(range1[0]) + 1
        if 'server_curport' not in node:
            range2 = node['server_portrange'].split('-')
            node['server_curport'] = int(range2[0]) + 1
        mach = machines.get(node['ip'])
        if node['ip'] in nodemgrips:
            raise ValueError('Error: %s exists, only one node_mgr can be run on a machine!' % node['ip'])
        nodemgrips.add(node['ip'])
        nodemgrmaps[node['ip']] = node
        if 'brpc_http_port' in node:
            addPortToMachine(portmap, node['ip'], node['brpc_http_port'])
        else:
            node['brpc_http_port'] = args.defbrpc_http_port_nodemgr
            addPortToMachine(portmap, node['ip'], args.defbrpc_http_port_nodemgr)
        if 'tcp_port' in node:
            addPortToMachine(portmap, node['ip'], node['tcp_port'])
        else:
            node['tcp_port'] = args.deftcp_port_nodemgr
            addPortToMachine(portmap, node['ip'], args.deftcp_port_nodemgr)
        if 'prometheus_port_start' in node:
            addPortToMachine(portmap, node['ip'], node['prometheus_port_start'])
        else:
            node['prometheus_port_start'] = args.defprometheus_port_start_nodemgr
            addPortToMachine(portmap, node['ip'], node['prometheus_port_start'])
        # The logic is that:
        # - if it is set, check every item is an absolute path.
        # - if it is not set, it is default to $basedir/{server_datadir, storage_datadir, storage_logdir, storage_waldir}
        for item in ["server_datadirs", "storage_datadirs", "storage_logdirs", "storage_waldirs"]:
            if item in node:
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

    ha_mode = meta.get('ha_mode', '')
    nodecnt = len(meta['nodes'])
    if ha_mode == '':
        if nodecnt > 1:
            ha_mode = 'mgr'
        else:
            ha_mode = 'no_rep'
    meta['ha_mode'] = ha_mode
    if nodecnt == 0 and not 'group_seeds' in meta:
        raise ValueError('Error: There must be at least one node in meta shard')
    if nodecnt > 1 and ha_mode == 'no_rep':
        raise ValueError('Error: ha_mode is no_rep, but there are multiple nodes in meta shard')
    elif nodecnt == 1 and ha_mode != 'no_rep':
        raise ValueError('Error: ha_mode is mgr/rbr, but there is only one node in meta shard')
    hasPrimary=False
    meta_addrs = []
    for node in meta['nodes']:
        # These attr should not be set explicitly.
        for attr in ['data_dir_path', 'log_dir_path', 'innodb_log_dir_path']:
            if attr in node:
                raise ValueError('%s can not be set explicitly for meta node %s' % (attr, node['ip']))
        if node['ip'] not in nodemgrips:
            nodem = get_default_nodemgr(args, machines, node['ip'], "storage")
            nodemgr['nodes'].append(nodem)
            nodemgrmaps[node['ip']] = nodem
            nodemgrips.add(node['ip'])
        # node['nodemgr'] = nodemgrmaps.get(node['ip'])
        nodemgrobj = nodemgrmaps.get(node['ip'])
        fix_nodemgr_nodetype(args, nodemgrobj, 'storage')
        if 'port' not in node:
            node['port'] = get_nodemgr_nextport(args, nodemgrobj, "storage", 2)
        addPortToMachine(portmap, node['ip'], node['port'])
        addto_usedports(args, nodemgrobj, 'storage', node['port'])
        set_storage_using_nodemgr(machines, node, nodemgrobj, "128MB")
        meta_addrs.append("%s:%s" % (node['ip'], str(node['port'])))
        if meta['ha_mode'] == 'mgr':
            if 'xport' not in node:
                node['xport'] = get_nodemgr_nextport(args, nodemgrobj, "storage", 1)
            addPortToMachine(portmap, node['ip'], node['xport'])
            addto_usedports(args, nodemgrobj, 'storage', node['xport'])
            if 'mgr_port' not in node:
                node['mgr_port'] = get_nodemgr_nextport(args, nodemgrobj, "storage", 1)
            addPortToMachine(portmap, node['ip'], node['mgr_port'])
            addto_usedports(args, nodemgrobj, 'storage', node['mgr_port'])
        if 'election_weight' not in node:
            node['election_weight'] = 50
        if 'is_primary' not in node:
            node['is_primary'] = False
        if node['is_primary']:
            if hasPrimary:
                raise ValueError('Error: Two primaries found in meta shard, there should be one and only one Primary specified !')
            else:
                hasPrimary = True
    if nodecnt > 0:
        if not hasPrimary:
            meta['nodes'][0]['is_primary'] = True

    if (len(meta_addrs) > 0):
        meta['group_seeds'] = ",".join(meta_addrs)

    if 'backup' in jscfg:
        if 'hdfs' in jscfg['backup']:
            node = jscfg['backup']['hdfs']
            addPortToMachine(portmap, node['ip'], node['port'])

    if 'xpanel' in jscfg:
        node = jscfg['xpanel']
        if 'port' not in node:
            node['port'] = 18080
        if 'name' not in node:
            node['name'] = 'xpanel_%d' % node['port']
        if 'imageType' not in node:
            node['imageType'] = 'url'
        if 'imageFile' not in node:
            node['imageFile'] = 'kunlun-xpanel-%s.tar.gz' % args.product_version

    for cluster in clusters:
        if 'name' not in cluster:
            cluster['name'] = getuuid()
        if  'ha_mode' not in cluster:
            cluster['ha_mode'] = 'mgr'
        if 'storage_template' not in cluster:
            cluster['storage_template'] = 'normal'
        ha_mode = cluster['ha_mode']
        validate_ha_mode(ha_mode)
        comps = cluster['comp']
        datas = cluster['data']
        for node in comps['nodes']:
            mach = machines.get(node['ip'])
            mach['haspg'] = True
            if node['ip'] not in nodemgrips:
                nodem = get_default_nodemgr(args, machines, node['ip'], "server")
                nodemgr['nodes'].append(nodem)
                nodemgrmaps[node['ip']] = nodem
                nodemgrips.add(node['ip'])
            nodemgrobj = nodemgrmaps.get(node['ip'])
            fix_nodemgr_nodetype(args, nodemgrobj, 'server')
            if 'port' not in node:
                node['port'] = get_nodemgr_nextport(args, nodemgrobj, "server", 2)
            addPortToMachine(portmap, node['ip'], node['port'])
            addto_usedports(args, nodemgrobj, 'server', node['port'])
            if 'mysql_port' not in node:
                node['mysql_port'] = get_nodemgr_nextport(args, nodemgrobj, "server", 2)
            addPortToMachine(portmap, node['ip'], node['mysql_port'])
            addto_usedports(args, nodemgrobj, 'server', node['mysql_port'])
            set_server_using_nodemgr(machines, node, nodemgrobj)
        i = 1
        for shard in datas:
            nodecnt = len(shard['nodes'])
            if nodecnt == 0:
                raise ValueError('Error: There must be at least one node in the shard')
            if ha_mode == 'no_rep' and nodecnt > 1:
                raise ValueError('Error: ha_mode is no_rep, but there are multiple nodes in the shard')
            elif nodecnt == 1 and ha_mode != 'no_rep':
                raise ValueError('Error: ha_mode is mgr/rbr, but there is only one node in the shard')
            hasPrimary = False
            for node in shard['nodes']:
                if node['ip'] not in nodemgrips:
                    nodem = get_default_nodemgr(args, machines, node['ip'], "storage")
                    nodemgr['nodes'].append(nodem)
                    nodemgrmaps[node['ip']] = nodem
                    nodemgrips.add(node['ip'])
                nodemgrobj = nodemgrmaps.get(node['ip'])
                fix_nodemgr_nodetype(args, nodemgrobj, 'storage')
                if 'port' not in node:
                    node['port'] = get_nodemgr_nextport(args, nodemgrobj, "storage", 2)
                addPortToMachine(portmap, node['ip'], node['port'])
                addto_usedports(args, nodemgrobj, 'storage', node['port'])
                set_storage_using_nodemgr(machines, node, nodemgrobj)
                if ha_mode == 'mgr':
                    if 'xport' not in node:
                        node['xport'] = get_nodemgr_nextport(args, nodemgrobj, "storage", 1)
                    addPortToMachine(portmap, node['ip'], node['xport'])
                    addto_usedports(args, nodemgrobj, 'storage', node['xport'])
                    if 'mgr_port' not in node:
                        node['mgr_port'] = get_nodemgr_nextport(args, nodemgrobj, "storage", 1)
                    addPortToMachine(portmap, node['ip'], node['mgr_port'])
                    addto_usedports(args, nodemgrobj, 'storage', node['mgr_port'])
                if 'election_weight' not in node:
                    node['election_weight'] = 50
                if 'is_primary' not in node:
                    node['is_primary'] = False
                if node['is_primary']:
                    if hasPrimary:
                        raise ValueError('Error: Two primaries found in %s-shard%d, there should be one and only one Primary specified !' % (cluster['name'], i))
                    else:
                        hasPrimary = True
            if nodecnt > 0:
                if not hasPrimary:
                    shard['nodes'][0]['is_primary'] = True
            i += 1

        if 'haproxy' in cluster:
            node = cluster['haproxy']
            addPortToMachine(portmap, node['ip'], node['port'])
            if 'mysql_port' in node:
                addPortToMachine(portmap, node['ip'], node['mysql_port'])
    if args.verbose:
        for node in nodemgr['nodes']:
            my_print(str(node))

def get_default_nodemgr(args, machines, ip, nodetype):
    mach = machines.get(ip)
    defpaths = {
            "server_datadirs": "server_datadir",
            "storage_datadirs": "storage_datadir",
            "storage_logdirs": "storage_logdir",
            "storage_waldirs": "storage_waldir",
        }
    node =  {
            'ip': ip,
            'brpc_http_port': args.defbrpc_http_port_nodemgr,
            "tcp_port": args.deftcp_port_nodemgr,
            "prometheus_port_start": args.defprometheus_port_start_nodemgr,
            'total_cpu_cores': 0,
            'total_mem': 0,
            'nodetype': 'none',
            'storage_portrange': args.defstorage_portrange_nodemgr,
            'server_portrange': args.defserver_portrange_nodemgr,
            'storage_curport': int(args.defstorage_portrange_nodemgr.split('-')[0]) + 1,
            'server_curport': int(args.defserver_portrange_nodemgr.split('-')[0]) + 1,
            'storage_usedports': [],
            'server_usedports': [],
            'valgrind': False,
            "skip": True
            }
    for item in ["server_datadirs", "storage_datadirs", "storage_logdirs", "storage_waldirs"]:
        node[item] = "%s/%s" % (mach['basedir'], defpaths[item])
    return node

def get_nodemgr_nextport(args, nodemgrobj, nodetype, incr=1):
    if nodetype == 'storage':
        port = nodemgrobj['storage_curport']
        nodemgrobj['storage_curport'] += incr
        return port
    else:
        port = nodemgrobj['server_curport']
        nodemgrobj['server_curport'] += incr
        return port

def fix_nodemgr_nodetype(args, nodemgrobj, addtype):
    if nodemgrobj['nodetype'] == 'both' or nodemgrobj['nodetype'] == addtype:
        pass
    elif nodemgrobj['nodetype'] == 'none':
        nodemgrobj['nodetype'] = addtype
    else:
        nodemgrobj['nodetype'] = 'both'

def addto_usedports(args, nodemgrobj, addtype, port):
    if addtype == 'storage':
        nodemgrobj['storage_usedports'].append(str(port))
    else:
        nodemgrobj['server_usedports'].append(str(port))

def get_servernodes_from_meta(args, metaseeds):
    conn = get_master_conn(args, metaseeds)
    cur = con.cursor()
    cur.close()
    conn.close()

def get_master_conn(args, metaseeds):
    mc = __import__('mysql.connector', globals(), locals(), [], -1)
    for addr in metaseeds.split(','):
        parts = addr.split(':')
        host = parts[0]
        port = 3306
        if len(parts) > 1:
            port = int(parts[1])
        mysql_conn_params = {}
        mysql_conn_params['host'] = host
        mysql_conn_params['port'] = port
        mysql_conn_params['user'] = args.user
        mysql_conn_params['password'] = args.password
        mysql_conn_params['database'] = 'Kunlun_Metadata_DB'
        conn = None
        csr = None
        try:
            conn = mc.connect(**mysql_conn_params)
            csr = conn.cursor()
            csr.execute("select @@super_read_only")
            row = csr.fetchone()
            if row is None or row[0] == '1':
                csr.close()
                csr = None
                conn.close()
                conn = None
                continue
            else:
                print "%s:%s is master" % (host, str(port))
                csr.close()
                return conn
        except mc.errors.InterfaceError as err:
            if conn is not None:
                conn.close()
            continue
    return None
