#!/bin/python2
# Copyright (c) 2019 ZettaDB inc. All rights reserved.
# This source code is licensed under Apache 2.0 License,
# combined with Common Clause Condition 1.0, as detailed in the NOTICE file.

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
        mysql_conn_params['use_pure'] = True
        conn = None
        csr = None
        try:
            conn = mysql.connector.connect(**mysql_conn_params)
            csr = conn.cursor()
            csr.execute("select @@super_read_only")
            row = csr.fetchone()
            if row is None or int(row[0]) == 1:
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

def delete_cluster(args):
    meta_conn = get_master_conn(args, args.seeds)
    csr = meta_conn.cursor()
    csr.execute("select id from db_clusters where name=%s", (args.cluster_name,))
    row = csr.fetchone()
    if row is None:
        csr.close()
        meta_conn.close()
        return
    cluster_id = row[0]
    meta_cursor0 = meta_conn.cursor()
    meta_cursor0.execute("start transaction")
    stmt = "delete from cluster_coldbackups where cluster_id=%s"
    meta_cursor0.execute(stmt, (cluster_id,))
    stmt = "delete from cluster_shard_backup_restore_log where cluster_id=%s"
    meta_cursor0.execute(stmt, (cluster_id,))
    stmt = "delete from comp_nodes where db_cluster_id=%s"
    meta_cursor0.execute(stmt, (cluster_id,))
    stmt = "delete from shard_nodes where db_cluster_id=%s"
    meta_cursor0.execute(stmt, (cluster_id,))
    stmt = "delete from shards where db_cluster_id=%s"
    meta_cursor0.execute(stmt, (cluster_id,))
    stmt = "delete from node_map_master where cluster_id=%s"
    meta_cursor0.execute(stmt, (cluster_id,))
    stmt = "delete from db_clusters where id=%s"
    meta_cursor0.execute(stmt, (cluster_id,))
    meta_cursor0.execute("commit")
    meta_cursor0.close()
    meta_conn.close()

if  __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Specify the arguments.')
    parser.add_argument('--seeds', type=str, help="The meta seeds", required=True)
    parser.add_argument('--user', type=str, help="The user used to connect meta", default='pgx')
    parser.add_argument('--password', type=str, help="The password used to connect meta", default='pgx_pwd')
    parser.add_argument('--cluster_name', type=str, help="The cluster name", required=True)

    args = parser.parse_args()
    delete_cluster(args)
