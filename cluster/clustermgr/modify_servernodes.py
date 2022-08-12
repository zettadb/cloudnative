#!/bin/python2
# Copyright (c) 2019 ZettaDB inc. All rights reserved.
# This source code is licensed under Apache 2.0 License,
# combined with Common Clause Condition 1.0, as detailed in the NOTICE file.

import json
import argparse
import mysql.connector

def get_nodemgr_nodes(filepath):
    f = open(filepath)
    obj = json.loads(f.read())
    f.close()
    return obj

def get_master_conn(args, metaseeds):
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
            conn = mysql.connector.connect(**mysql_conn_params)
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
        except mysql.connector.errors.InterfaceError as err:
            if conn is not None:
                conn.close()
            continue
    return None

def install_nodemgr_nodes(args):
    meta_conn = get_master_conn(args, args.seeds)
    nodes = get_nodemgr_nodes(args.config)
    meta_cursor = meta_conn.cursor(prepared=True)
    meta_cursor0 = meta_conn.cursor()
    meta_cursor0.execute("start transaction")
    stmt = "insert into server_nodes(hostaddr, total_mem, total_cpu_cores, comp_datadir, \
            datadir, logdir, wal_log_dir, machine_type, nodemgr_prometheus_port, port_range, used_port, \
            current_port_pos) values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    for node in nodes:
        if node['skip'] or node['nodetype'] == 'none':
            continue
        if node['nodetype'] == 'both' or node['nodetype'] == 'storage':
            meta_cursor.execute(stmt, (node['ip'], node['total_mem'], node['total_cpu_cores'], node['server_datadirs'], 
                node['storage_datadirs'], node['storage_logdirs'], node['storage_waldirs'], 'storage', 
                node['prometheus_port_start'], node['storage_portrange'], ",".join(node['storage_usedports']) + ",", node['storage_curport']))
        if node['nodetype'] == 'both' or node['nodetype'] == 'server':
            meta_cursor.execute(stmt, (node['ip'], node['total_mem'], node['total_cpu_cores'], node['server_datadirs'], 
                node['storage_datadirs'], node['storage_logdirs'], node['storage_waldirs'], 'computer', 
                node['prometheus_port_start'], node['server_portrange'], ",".join(node['server_usedports']) + ",", node['server_curport']))

    stmt = "update server_nodes set current_port_pos=%s, used_port=concat(used_port, ',', %s) where hostaddr=%s and machine_type=%s"
    for node in nodes:
        if node['nodetype'] == 'none' or not node['skip']:
            continue
        if len(node['storage_usedports']) > 0:
            meta_cursor.execute(stmt, (node['storage_curport'], ",".join(node['storage_usedports']) + ",", node['ip'], 'storage'))
        if len(node['server_usedports']) > 0:
            meta_cursor.execute(stmt, (node['server_curport'], ",".join(node['server_usedports']) + ",", node['ip'], 'computer'))

    meta_cursor0.execute("commit")
    meta_cursor.close()
    meta_cursor0.close()
    meta_conn.close()

def clean_nodemgr_nodes(args):
    meta_conn = get_master_conn(args, args.seeds)
    if meta_conn is None:
        return
    nodes = get_nodemgr_nodes(args.config)
    meta_cursor = meta_conn.cursor(prepared=True)
    meta_cursor0 = meta_conn.cursor()
    meta_cursor0.execute("start transaction")
    stmt1 = "delete t2 from server_nodes_stats t2 inner join server_nodes t1 using(id) where t1.hostaddr=%s"
    stmt2 = "delete from server_nodes t1 where t1.hostaddr=%s"
    for node in nodes:
        if node['skip']:
            continue
        meta_cursor.execute(stmt1, (node['ip'],))
        meta_cursor.execute(stmt2, (node['ip'],))
    meta_cursor0.execute("commit")
    meta_cursor.close()
    meta_cursor0.close()
    meta_conn.close()

if  __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Specify the arguments.')
    actions=["install", "clean"]
    parser.add_argument('--config', type=str, help="The config path for nodemgr nodes", required=True)
    parser.add_argument('--action', type=str, help="The action", choices=actions, required=True)
    parser.add_argument('--seeds', type=str, help="The meta seeds", required=True)
    parser.add_argument('--user', type=str, help="The user used to connect meta", default='pgx')
    parser.add_argument('--password', type=str, help="The password used to connect meta", default='pgx_pwd')

    args = parser.parse_args()

    if args.action == 'install':
        install_nodemgr_nodes(args)
    elif args.action == 'clean':
        clean_nodemgr_nodes(args)
    else:
        # just defensive, for more more actions later.
        pass

