import requests
import pymysql
import json
import yaml
import argparse
from time import sleep

def readFile():
    global shards, dataHost, nodes, datadir, user_name, fullsync_level, table_list
    global logdir, wal_log_dir, comp_datadir, total_mem, total_cpu_cores, dbcfg, postad, mysql_port_range
    global nick_name, max_storage_size, max_connections, mgrPort, mgrHost, ha_mode, innodb_size
    f = open(files,encoding='utf-8')
    of = yaml.safe_load(f.read())
    table_list = of["table_list"]
    dataHost = of["storage"]
    shards = str(of["shards"])
    user_name = of["user_name"]
    dbcfg = str(of["dbcfg"])
    nodes = str(of["nodes"])
    mysql_port_range = of["mysql_port_range"]
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

def addShards(user_name, shards, nodes, hostaddr):
    add_shards = json.dumps({
    "version":"1.0",
    "job_id":"",
    "job_type":"add_shards",
    "timestamp":"1435749309",
    "user_name":user_name,
    "paras":{
        "cluster_id":"1",
        "shards":shards,
        "nodes":nodes,

        "storage_iplists":[
            hostaddr
        ]
    }
})

    res = requests.post(postad, data=add_shards)
    print(res.status_code, res.reason)
    print(res.text)

def scaleOut(user_name, dst_shard_id, src_shard_id, table_list):
    scale_out = json.dumps({
  "version": "1.0",
  "job_id":"",
  "job_type": "expand_cluster",
  "timestamp" : "1435749309",
  "user_name":user_name,
  "paras": {
    "cluster_id": "1",
    "dst_shard_id": dst_shard_id,
    "src_shard_id": src_shard_id,
    "table_list": [
      table_list
    ]
  }
})

def runTest():
    for i in dataHost:
        createStorage(user_name, i, mysql_port_range, datadir, logdir, wal_log_dir, comp_datadir, total_mem, total_cpu_cores)

    addShards(user_name, shards, nodes, hostaddr)

    tableNum = 0
    for i in table_list:
        tableNum = tableNum + 1
    
    if tableNum >= shards:
        shardList=[]

        for i in shards:
            shardList.append(shardNum)
        
        for i in shardNum:

            scaleOut(user_name, )
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'install')
    parser.add_argument('--config', default='scaleOut.ymal', help = 'the configure yaml file')
    args = parser.parse_args()
    files = args.config
    readFile()
    runTest()
