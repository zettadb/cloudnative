import requests
import pymysql
import json
import yaml
import argparse
from time import sleep

def readFile():
    global shards, compHost, dataHost, nodes, comps, pgsql_port_range, datadir, user_name, fullsync_level
    global logdir, wal_log_dir, comp_datadir, total_mem, total_cpu_cores, dbcfg, postad, mysql_port_range
    global nick_name, max_storage_size, max_connections, mgrPort, mgrHost, ha_mode, innodb_size
    f = open(files,encoding='utf-8')
    of = yaml.safe_load(f.read())
    compHost = of["computer"]
    dataHost = of["storage"]
    shards = str(of["shards"])
    user_name = of["user_name"]
    dbcfg = str(of["dbcfg"])
    nodes = str(of["nodes"])
    comps = str(of["comps"])
    mysql_port_range = of["mysql_port_range"]
    pgsql_port_range = of["pgsql_port_range"]
    datadir = of["datadir"]
    logdir = of["logdir"]
    wal_log_dir = of["wal_log_dir"]
    comp_datadir = of ["comp_datadir"]
    total_mem = str(of["total_mem"])
    fullsync_level = str(of["fullsync_level"])
    total_cpu_cores = str(of["total_cpu_cores"])
    innodb_size = str(of["innodb_size"])
    nick_name = of["nick_name"]
    max_storage_size = str(of["max_storage_size"])
    max_connections = str(of["max_connections"])
 #   mgrPort = of["clusterMgrInfo"]["port"]
 #   mgrHost = of["clusterMgrInfo"]["host"]
    ha_mode = of["ha_mode"]
    metaPort = of["MetaPrimaryNode"]["port"]
    metaHost = of["MetaPrimaryNode"]["host"]
    db = pymysql.connect(host = metaHost, port = int(metaPort), user = "pgx", password = "pgx_pwd", database = "kunlun_metadata_db")
    cur = db.cursor()
    cur.execute("select hostaddr from cluster_mgr_nodes where  member_state = 'source'")
    MgrHost = cur.fetchone()
    cur.execute("select port from cluster_mgr_nodes where  member_state = 'source'")
    MgrPort = cur.fetchone()
    db.commit()
    cur.close()
    db.close()
    print(MgrPort)
    print(MgrHost)
    mgrPort = str(MgrPort)
    mgrHost = str(MgrHost)
    mgrPort = mgrPort.replace('(','')
    mgrPort = mgrPort.replace(",)","")
    mgrHost = mgrHost.replace("('","")
    mgrHost = mgrHost.replace("',)","")
    print(mgrPort)
    print(mgrHost)
    postad = "http://%s:%s/HttpService/Emit" % (mgrHost, mgrPort)


header = {
        "cookie": "cookie",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
}
def createComputer(user_name, host, port_range, datadir, logdir, wal_log_dir, comp_datadir, total_mem, total_cpu_cores):
    create_computer = json.dumps({
        "version":"1.0",
        "job_id":"",
        "job_type":"create_machine",
        "timestamp":"1435749309",
        "user_name": user_name,
        "paras":{
            "hostaddr": host,
            "machine_type": "computer",
            "port_range": port_range,
            "rack_id":"1",
            "datadir": datadir,
            "logdir": logdir,
            "wal_log_dir": wal_log_dir,
            "comp_datadir": comp_datadir,
            "total_mem": total_mem,
            "total_cpu_cores": total_cpu_cores
        }
    })
    #print(create_computer + '\n')
    #res = requests.post(postad, data=create_computer, headers=header)
    res = requests.post(postad, data=create_computer)
    print("create computer machine host = %s, port_range = %s" % (host, port_range))
    print(res.status_code, res.reason)
    print(res.text)


def createStorage(user_name, hostaddr, port_range, datadir, logdir, wal_log_dir, comp_datadir, total_mem, total_cpu_cores):
    create_storage = json.dumps({
    "version":"1.0",
    "job_id":"",
    "job_type":"create_machine",
    "timestamp":"1435749309",
    "user_name": user_name,
    "paras":{
        "hostaddr": hostaddr,
        "machine_type": "storage",
        "port_range": port_range,
        "rack_id": "1",
        "datadir": datadir,
        "logdir": logdir,
        "wal_log_dir": wal_log_dir,
        "comp_datadir": comp_datadir,
        "total_mem": total_mem,
        "total_cpu_cores":total_cpu_cores
    }
})
    #print(create_storage + '\n')
    #res = requests.post(postad, data=create_storage, headers=header)
    res = requests.post(postad, data=create_storage)
    print("create storage machine host = %s, port_range = %s" % (hostaddr, port_range))
    print(res.status_code, res.reason)
    print(res.text)

def createCluster(user_name, nick_name, ha_mode, shards, nodes, comps, max_storage_size, max_connections, cpu_cores, innodb_size, dbcfg, fullsync_level, storage_iplists, computer_iplists):
    create_cluster  = json.dumps({
    "version":"1.0",
    "job_id":"",
    "job_type":"create_cluster",
    "timestamp":"1435749309",
    "user_name": user_name,
    "paras":{
        "nick_name": nick_name,
        "ha_mode": ha_mode,
        "shards": shards,
        "nodes": nodes,
        "comps": comps,
        "max_storage_size": max_storage_size,
        "max_connections": max_connections,
        "cpu_cores": cpu_cores,
        "innodb_size": innodb_size,
        "dbcfg": dbcfg,
        "fullsync_level": fullsync_level,
        "storage_iplists":
            storage_iplists
        ,
        "computer_iplists":
            computer_iplists
        }
    })
    print(create_cluster + '\n')
    #res = requests.post(postad, data=create_cluster, headers=header)
    res = requests.post(postad, data=create_cluster)
    print("create cluster...")
    print(res.status_code, res.reason)
    print(res.text)


def runTest():
    for i in compHost:
        createComputer(user_name, i, pgsql_port_range, datadir, logdir, wal_log_dir, comp_datadir, total_mem, total_cpu_cores)
        #sleep(1)

    for i in dataHost:
        createStorage(user_name, i, mysql_port_range, datadir, logdir, wal_log_dir, comp_datadir, total_mem, total_cpu_cores)
        #sleep(1)
    
    createCluster(user_name, nick_name, ha_mode, shards, nodes, comps, max_storage_size, max_connections, total_cpu_cores, innodb_size, dbcfg, fullsync_level, dataHost, compHost)

def deleteTest():
    delete_cluster  = json.dumps({
    "version":"1.0",
    "job_id":"",
    "job_type":"delete_cluster",
    "timestamp":"1435749309",
    "user_name":user_name,
    "paras":{
        "cluster_name":nick_name
    }
})
    print(delete_cluster + '\n')
    res = requests.post(postad, data=delete_cluster)
    print("delete cluster...")
    print(res.status_code, res.reason)
    print(res.text)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'install')
    parser.add_argument('--config', default='config.ymal', help = 'the configure yaml file')
    parser.add_argument('--type', default='install' , help = 'can be "install", "delete"')
    args = parser.parse_args()
    types = args.type
    files = args.config
    if types == 'install':
        readFile()
        runTest()
    elif types == 'delete':
        readFile()
        deleteTest()

