#!/bin/python

import os
import sys
import re
import time
import random
import fcntl
import struct
import socket
import subprocess
import json
import shlex


def param_replace(string, rep_dict):
    pattern = re.compile("|".join([re.escape(k) for k in rep_dict.keys()]), re.M)
    return pattern.sub(lambda x: rep_dict[x.group(0)], string)

def make_mgr_args(config_path, replace_items, target_node_index):
    jsconf = open(config_path)
    jstr = jsconf.read()
    jscfg = json.loads(jstr)

    nodeidx = target_node_index
    group_uuid = jscfg['group_uuid']
    idx = 0
    white_list = ''
    local_addr = ''
    local_ip = ''
    seeds = ''
    is_master_node = False
    weight = 50
    mgr_port = 0
    server_xport = 0
    server_port  = 0
    innodb_buffer_pool_size = 0
    server_data_prefix = ''
    server_log_prefix = ''
    db_inst_user = ''

    for val in jscfg['nodes']:
        if val['is_primary'] == True and idx == nodeidx:
            is_master_node = True
        if white_list != '':
            white_list = white_list + ','
            seeds = seeds + ','

        white_list = white_list + val['ip']
        seeds = seeds + val['ip'] + ':' + str(val['mgr_port'])

        if idx == nodeidx:
            local_ip = val['ip']
            local_addr = val['ip'] + ':' + str(val['mgr_port'])
            mgr_port = val['mgr_port']
            weight = val['election_weight']
            server_port = val['port']
            server_xport = val['xport']
            innodb_buffer_pool_size = val['innodb_buffer_pool_size']
            server_data_prefix = val['data_dir_path']
            server_log_prefix = val['log_dir_path']
            db_inst_user = val['user']

        idx = idx + 1

    mgr_num_nodes = idx + 1
    if local_addr == '' or nodeidx < 0 or nodeidx >= mgr_num_nodes:
        raise ValueError("Config error, target_node_index must be in [0, {}).".format(mgr_num_nodes))
    if seeds == '':
        raise RuntimeError("Config error, no primary node specified.")

    if server_xport == mgr_port or server_port == mgr_port or server_port == server_xport :
        raise ValueError("Config error, MGR port(" + str(mgr_port) + "), client regular port(" +
			str(server_port) + ") and X protocol port(" + str(server_xport) + ") must be different.")
    data_path = server_data_prefix + "/" + str(server_port)
    prod_dir = data_path + "/prod"
    data_dir = data_path + "/dbdata_raw/data"
    innodb_dir = data_path + "/dbdata_raw/dbdata"
    
    log_path = server_log_prefix + "/" + str(server_port)
    log_dir = log_path + "/dblogs"
    tmp_dir = log_path + "/dblogs/tmp"
    log_relay = log_path + "/dblogs/relay"
    log_bin_arg = log_path + "/dblogs/bin"
    log_arch = log_path + "/dblogs/arch"

    replace_items["place_holder_ip"] = local_ip
    replace_items["place_holder_mgr_recovery_retry_count"] = str(mgr_num_nodes*100)
    replace_items["place_holder_mgr_local_address"] = local_addr
    replace_items["place_holder_mgr_seeds"] = seeds
    replace_items["place_holder_mgr_whitelist"] = white_list
    replace_items["place_holder_mgr_member_weight"] = str(weight)
    replace_items["place_holder_mgr_group_name"] = group_uuid
    replace_items["prod_dir"] = prod_dir
    replace_items["data_dir"] = data_dir
    replace_items["innodb_dir"] = innodb_dir
    replace_items["log_dir"] = log_dir
    replace_items["tmp_dir"] = tmp_dir
    replace_items["log_relay"] = log_relay
    replace_items["log_bin_arg"] = log_bin_arg
    replace_items["log_arch"] = log_arch
    replace_items["place_holder_innodb_buffer_pool_size"] = innodb_buffer_pool_size
    replace_items["place_holder_x_port"] =str(server_xport)
    replace_items["place_holder_port"] = str(server_port)
    replace_items["place_holder_user"] = db_inst_user

    os.makedirs(prod_dir)
    os.makedirs(data_dir)
    os.makedirs(innodb_dir)
    os.makedirs(log_dir)
    os.makedirs(tmp_dir)
    os.makedirs(log_relay)
    os.makedirs(log_bin_arg)
    os.makedirs(log_arch)
    jsconf.close()
    return is_master_node, server_port, data_path, log_path, log_dir, db_inst_user

def generate_cnf_file(config_template_file, install_path,  server_id, cluster_id, shard_id, config_path, target_node_index):
    replace_items = {
	    "base_dir": install_path,
	    "place_holder_server_id": str(server_id),
	    "place_holder_shard_id": str(shard_id),
	    "place_holder_cluster_id": str(cluster_id),
    }
    is_master, server_port, data_path, log_path, log_dir, user = make_mgr_args(config_path, replace_items, target_node_index)
    config_template = open(config_template_file, 'r').read()
    conf = param_replace(config_template, replace_items)
    etc_path = install_path + "/etc"
    if not os.path.exists(etc_path):
	os.mkdir(etc_path)
    cnf_file_path = etc_path+"/my_"+ str(server_port) +".cnf"
    cnf_file = open(cnf_file_path, 'w')
    cnf_file.write(conf)
    cnf_file.close()
    os.system("sed -e 's/#skip_name_resolve=on/skip_name_resolve=on/' -i " + cnf_file_path)
    os.system("sed -e 's/#super_read_only=OFF/super_read_only=ON/' -i " + cnf_file_path)
    os.system("sed -e 's/^#group_replication_/group_replication_/' -i " + cnf_file_path)
    os.system("sed -e 's/^#clone_/clone_/' -i " + cnf_file_path)

def print_usage():
    print 'Usage: restore-mysql.py config=/path/of/config/file target_node_index=idx [dbcfg=/db/config/template/path/template.cnf] [cluster_id=ID] [shard_id=N] [server_id=N]'

if __name__ == "__main__":
    try:
        args = dict([arg.split('=') for arg in sys.argv[1:]])
        if not args.has_key('config') or not args.has_key('target_node_index'):
            print_usage()
            raise RuntimeError('Must specify config and target_node_index arguments.')
        config_path = args["config"]
        target_node_index = int(args["target_node_index"])

        shard_id = 0
        cluster_id = 0
        if args.has_key('cluster_id'):
            cluster_id = int(args['cluster_id'])
        if args.has_key('shard_id'):
            shard_id = int(args['shard_id'])
        if args.has_key('server_id'):
            server_id = int(args['server_id'])
        else:
            server_id = str(random.randint(1,65535))

        if args.has_key('dbcfg') :
            config_template_file = args['dbcfg']
        else:
            config_template_file = "./template.cnf"
        if not os.path.exists(config_template_file):
            raise ValueError("DB config template file {} doesn't exist!".format(config_template_file))
        install_path = os.getcwd()[:-8]
        generate_cnf_file(config_template_file, install_path, server_id, cluster_id, shard_id, config_path, target_node_index)
    except KeyError, e:
        print_usage()
        print e
