#!/bin/python2
# Copyright (c) 2019 ZettaDB inc. All rights reserved.
# This source code is licensed under Apache 2.0 License,
# combined with Common Clause Condition 1.0, as detailed in the NOTICE file.

import json
import argparse
import mysql.connector

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

def get_server_uuid(args, host, port, user, password):
    con_params = {}
    con_params['host'] = host
    con_params['port'] = port
    con_params['user'] = user
    con_params['password'] = password
    con_params['database'] = 'kunlun_sysdb'
    conn = None
    res = ""
    try:
        conn = mysql.connector.connect(**con_params)
        csr = conn.cursor()
        csr.execute("select @@server_uuid")
        row = csr.fetchone()
        res = row[0]
        csr.close()
        conn.close()
        conn = None
    except mysql.connector.errors.InterfaceError as err:
        if conn is not None:
            conn.close()
    return res

def get_cluster_id(args, conn, host, port):
    stmt = "select db_cluster_id from shard_nodes where hostaddr=%s and port=%s"
    res = -1
    try:
        csr = conn.cursor()
        csr.execute(stmt, (host, port))
        row = csr.fetchone()
        res = int(row[0])
        csr.close()
    except mysql.connector.errors.InterfaceError as err:
        pass
    return res

def get_pnode_info(args, nodes):
    n = None
    for node in nodes:
        if node['is_primary']:
            n = node
            break
    pstr = "%s_%d" % (n['ip'], n['port'])
    puuid = get_server_uuid(args, n['ip'], n['port'], 'pgx', 'pgx_pwd')
    return [pstr, puuid, n]

def get_shard_info(args, mcon):
    f = open(args.shardscfg)
    obj = json.loads(f.read())
    f.close()
    info = get_pnode_info(args, obj['nodes'])
    pnode = info[2]
    if args.type == 'meta':
        cluster_id = -1
    else:
        cluster_id = get_cluster_id(args, mcon, pnode['ip'], pnode['port'])
    for node in obj['nodes']:
        if node['is_primary']:
            continue
        node['master_host'] = info[0]
        node['master_uuid'] = info[1]
        node['cluster_id'] = cluster_id
    return obj 

def add_cluster(args):
    meta_conn = get_master_conn(args, args.seeds)
    shardobj = get_shard_info(args, meta_conn)
    stmt = "insert into node_map_master(cluster_id, node_host, master_host, master_uuid) values(%s,%s,%s,%s)"
    csr = meta_conn.cursor()
    csr.execute("start transaction")
    for node in shardobj['nodes']:
        if node['is_primary']:
            continue
        csr.execute(stmt, (node['cluster_id'], "%s_%d" % (node['ip'], node['port']), node['master_host'], node['master_uuid']))
        #print stmt % (node['cluster_id'], "%s_%d" % (node['ip'], node['port']), node['master_host'], node['master_uuid'])
    csr.execute("commit")
    meta_conn.close()

if  __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Specify the arguments.')
    parser.add_argument('--seeds', type=str, help="The meta seeds", required=True)
    parser.add_argument('--user', type=str, help="The user used to connect meta", default='pgx')
    parser.add_argument('--password', type=str, help="The password used to connect meta", default='pgx_pwd')
    types = ['meta', 'data']
    parser.add_argument('--type', type=str, help="The config type", choices=types, required=True)
    parser.add_argument('--shardscfg', type=str, help="The shard config file", required=True)

    args = parser.parse_args()
    add_cluster(args)
