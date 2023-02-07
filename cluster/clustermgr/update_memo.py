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

def update_memo(args):
    meta_conn = get_master_conn(args, args.seeds)
    f = open(args.memocfg)
    memostr = f.read()
    memostr = memostr.replace("\n","")
    f.close()
    stmt = "update db_clusters set memo=%s where name=%s"
    csr = meta_conn.cursor()
    csr.execute("start transaction")
    csr.execute(stmt, (memostr, args.cluster))
    csr.execute("commit")
    meta_conn.close()

if  __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Specify the arguments.')
    parser.add_argument('--seeds', type=str, help="The meta seeds", required=True)
    parser.add_argument('--user', type=str, help="The user used to connect meta", default='pgx')
    parser.add_argument('--password', type=str, help="The password used to connect meta", default='pgx_pwd')
    parser.add_argument('--cluster', type=str, help="The cluster name", required=True)
    parser.add_argument('--memocfg', type=str, help="The memo json file", required=True)

    args = parser.parse_args()
    update_memo(args)
