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

def get_storage_conn(host, port, user, password, dbname='kunlun_sysdb'):
    mysql_conn_params = {}
    mysql_conn_params['host'] = host
    mysql_conn_params['port'] = port
    mysql_conn_params['user'] = user
    mysql_conn_params['password'] = password
    mysql_conn_params['database'] = dbname
    mysql_conn_params['use_pure'] = True
    conn = None
    try:
        conn = mysql.connector.connect(**mysql_conn_params)
    except mysql.connector.errors.InterfaceError as err:
        pass
    return conn

def get_server_uuid(args, host, port, user, password):
    con_params = {}
    con_params['host'] = host
    con_params['port'] = port
    con_params['user'] = user
    con_params['password'] = password
    con_params['database'] = 'kunlun_sysdb'
    con_params['use_pure'] = True
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

# the key is set_variables
# the data should be like:
# {'op':'add', "elements": [setobj1, setobj2, etc]}
# the format for setobj is like:
# {"ip":str, "port":int, "variable_name":str, "value":int/str}
def process_variables(varobj):
    eles = varobj['elements']
    for obj in eles:
        conn =  get_storage_conn(obj['ip'], obj['port'], 'pgx', 'pgx_pwd')
        csr = conn.cursor()
        # currently supports integer and string.
        if obj['type'] == 'integer':
            csr.execute("set global %s=%d" % (obj['variable_name'], obj['value']))
        elif obj['type'] == 'string':
            csr.execute("set global %s='%s'" % (obj['variable_name'], obj['value']))
        csr.close()
        conn.close()

# the key is hdfsbackup
# The data should be like:
# {"host": str, "port": int}
def process_hdfs(conn, hdfsobj):
    # currently hdfsobj.op is not read, since only one op: add
    data = hdfsobj['data']
    host = data['host']
    port = data['port']
    url = "hdfs://%s:%d" % (host, port)
    meta_cursor0 = conn.cursor()
    meta_cursor0.execute("start transaction")
    stmt = "insert into backup_storage(name, stype, conn_str, hostaddr, port) values(%s,%s,%s,%s,%s)"
    meta_cursor0.execute(stmt, ("hdfs_backup1", "HDFS", url, host, port))
    meta_cursor0.execute("commit")
    meta_cursor0.close()

# the key is sshbackup
# the data should be like:
# {"host": str, "port": int, "user": str, "targetRoot": str}
def process_ssh(conn, sshobj):
    # currently hdfsobj.op is not read, since only one op: add
    data = sshobj['data']
    meta_cursor0 = conn.cursor()
    meta_cursor0.execute("start transaction")
    stmt = "insert into backup_storage(name, stype, hostaddr, port, user_name, extra) values(%s,%s,%s,%s,%s,%s)"
    meta_cursor0.execute(stmt, ("ssh_backup1", "SSH", data.host, data.port, data.user, data.targetRoot))
    meta_cursor0.execute("commit")
    meta_cursor0.close()

# the key is: elasticsearch
# The data should be like:
# {"host": str, "port": int}
def process_elasticsearch(conn, esobj):
    data = esobj['data']
    host = data['host']
    port = data['port']
    meta_cursor0 = conn.cursor()
    meta_cursor0.execute("start transaction")
    stmt = "insert into cluster_es_conf(is_install, es_hostaddr, es_port) values(%s,%s,%s)"
    meta_cursor0.execute(stmt, ("yes", host, port))
    meta_cursor0.execute("commit")
    meta_cursor0.close()

# the key is 'datacenters'
# The data should be like:
# {"elements":[dcobj1, dcobj2, dcobj3, etc]}
# currently for dcobj, the format is like:
#   {"name":str, "province": str, "city": str}
def process_datacenters(conn, dcobj):
    meta_cursor0 = conn.cursor()
    meta_cursor0.execute("start transaction")
    stmt = "insert into data_centers(name, province, city) values(%s, %s, %s)"
    for ele in dcobj['elements']:
        if ele.get('skip', False):
            continue
        meta_cursor0.execute(stmt, (ele['name'], ele['province'], ele['city']))
    meta_cursor0.execute("commit")
    meta_cursor0.close()

# the key is node_manager
# The op currently support: add/clean
# general object format is:
# {'op':'add'|'remove', 'elements':[obj1, obj2, etc]}
def process_servernodes(conn, snobj):
    if snobj['op'] == 'add':
        add_servernodes(conn, snobj)
    elif snobj['op'] == 'remove':
        remove_servernodes(conn, snobj)
    else:
        raise ValueError('invalid op for process_servernodes: %s' %  snobj['op'])

# This is add, the object is like:
# {'op': 'add', 'elements': [obj1, obj2, etc.]}
def add_servernodes(meta_conn, snobj):
    nodes = snobj['elements']
    meta_cursor = meta_conn.cursor(prepared=True)
    meta_cursor0 = meta_conn.cursor()
    meta_cursor0.execute("start transaction")
    stmt = "insert into server_nodes(hostaddr, total_mem, total_cpu_cores, comp_datadir, \
            datadir, logdir, wal_log_dir, machine_type, nodemgr_prometheus_port, port_range, used_port, \
            current_port_pos, nodemgr_port, nodemgr_tcp_port, dc_id) values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, \
            %s, %s, (select id from data_centers where name=%s))"
    for node in nodes:
        if 'dc' not in node:
            node['dc'] = 'unknown'
        if node['skip'] or node['nodetype'] == 'none':
            continue
        if node['nodetype'] == 'both' or node['nodetype'] == 'storage':
            meta_cursor.execute(stmt, (node['ip'], node['total_mem'], node['total_cpu_cores'], node['server_datadirs'], 
                node['storage_datadirs'], node['storage_logdirs'], node['storage_waldirs'], 'storage', 
                node['prometheus_port_start'], node['storage_portrange'], ",".join(node['storage_usedports']) + ",",
                node['storage_curport'], node["brpc_http_port"], node["tcp_port"], node['dc']))
        if node['nodetype'] == 'both' or node['nodetype'] == 'server':
            meta_cursor.execute(stmt, (node['ip'], node['total_mem'], node['total_cpu_cores'], node['server_datadirs'], 
                node['storage_datadirs'], node['storage_logdirs'], node['storage_waldirs'], 'computer', 
                node['prometheus_port_start'], node['server_portrange'], ",".join(node['server_usedports']) + ",",
                node['server_curport'], node["brpc_http_port"], node["tcp_port"], node['dc']))
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

# This is used for remove, object is like:
# {'op':'remove', 'elements':[obj1, obj2, etc]}
def remove_servernodes(meta_conn, snobj):
    nodes = snobj['elements']
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

# the key is nodemapmaster
# The format for the object is:
# {'op':'add', 'elements': [pair obj1, pair obj2, etc]}
# the pair obj is like:  {'host':str 'port':int, 'master_host':str, 'master_port':int, 'is_meta': boolean}
def process_nodemapmaster(meta_conn, nmmobj):
    nodes = nmmobj['elements']
    stmt = "insert into node_map_master(cluster_id, node_host, master_host, master_uuid) values(%s,%s,%s,%s)"
    csr = meta_conn.cursor()
    csr.execute("start transaction")
    for node in nodes:
        if node['is_meta']:
            cluster_id = -1
        else:
            cluster_id = get_cluster_id(args, meta_conn, node['host'], node['port'])
        master_uuid = get_server_uuid(args, node['master_host'], node['master_port'], 'pgx', 'pgx_pwd')
        csr.execute(stmt, (cluster_id, "%s_%d" % (node['host'], node['port']),
            "%s_%d" % (node['master_host'], node['master_port']), master_uuid))
    csr.execute("commit")
    csr.close()

# the key is 'delete_cluster'
# the format for the object is:
# {'op':'remove', 'elements': [name1, name2, etc.]}
def process_deleteclusters(meta_conn, nameobj):
    names = nameobj['elements']
    for name in names:
        csr = meta_conn.cursor()
        csr.execute("select id from db_clusters where name=%s", (args.cluster_name,))
        row = csr.fetchone()
        if row is None:
            csr.close()
            continue
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


# the key is cluster_info
# the format is like:
# {'op':'add', "elements":[memo1, memo2, etc]}
# while memo object has the format like:
# {"name": str, "memo":json_object}
def process_clusterinfo(meta_conn, memobj):
    items = memobj['elements']
    memostmt = "update db_clusters set memo=%s where name=%s"
    sidstmt = 'select a.id from shards a, db_clusters b where a.db_cluster_id=b.id and b.name=%s'
    for item in items:
        cname = item['name']
        jsonobj = item['memo']
        stostmt_orig = "insert into cluster_shard_topology(cluster_id, shard_id, max_commit_log_id, max_ddl_log_id) values((select id from db_clusters where name='{}'),%s, (select IFNULL(max(id),0) from commit_log_{}), (select IFNULL(max(id),0) from ddl_ops_log_{}));"
        csr = meta_conn.cursor()
        csr.execute(sidstmt, (cname,))
        sid_rows = csr.fetchall()
        sid_list = []
        for sid_row in sid_rows:
            sid_list.append(str(sid_row[0]))
        csr.close()
        sid_str = ",".join(sid_list)
        stostmt = stostmt_orig.format(cname, cname, cname)
        csr = meta_conn.cursor()
        csr.execute("start transaction")
        csr.execute(stostmt, (sid_str,))
        jsonstr = json.JSONEncoder().encode(jsonobj)
        csr.execute(memostmt, (jsonstr, cname))
        csr.execute("commit")
        csr.close()

def process_change(args):
    f = open(args.config)
    obj = json.loads(f.read())
    f.close()

    if 'set_variables' in obj:
        process_variables(obj['set_variables'])

    meta_conn = get_master_conn(args, args.seeds)
    if 'datacenters' in obj:
        process_datacenters(meta_conn, obj['datacenters'])
    if 'node_manager' in obj:
        process_servernodes(meta_conn, obj['node_manager'])
    if 'nodemapmaster' in obj:
        process_nodemapmaster(meta_conn, obj['nodemapmaster'])
    if 'hdfsbackup' in obj:
        process_hdfs(meta_conn, obj['hdfsbackup'])
    if 'sshbackup' in obj:
        process_ssh(meta_conn, obj['sshbackup'])
    if 'elasticsearch' in obj:
        process_elasticsearch(meta_conn, obj['elasticsearch'])
    if 'delete_cluster' in obj:
        process_deleteclusters(meta_conn, obj['delete_cluster'])
    if 'cluster_info' in obj:
        process_clusterinfo(meta_conn, obj['cluster_info'])
    meta_conn.close()

# Generally, the while config file is a large json object
# inside the object, it is divided into several sub-object,
# every sub-object has two member:
#   - op: usually it is add/delete/modify or other, it is read by processor 
#   - data: The real data used to modify the kunlun_metadata_db's table.
if  __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Specify the arguments.')
    parser.add_argument('--seeds', type=str, help="The meta seeds", required=True)
    parser.add_argument('--user', type=str, help="The user used to connect meta", default='pgx')
    parser.add_argument('--password', type=str, help="The password used to connect meta", default='pgx_pwd')
    parser.add_argument('--config', type=str, help="The config file about modificagtions", required=True)

    args = parser.parse_args()
    process_change(args)
