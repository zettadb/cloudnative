import subprocess
from time import sleep
import json
import argparse
import os
import psycopg2
import pymysql

def readJsonFile():
    OpenCluster=open(install, encoding='utf-8')
    ReadCluster=json.loads(OpenCluster.read())

    CompTotal=ReadCluster['cluster']['comp']['nodes']
    if types == 'cluster_mgr':
        global insBin, serDat
        insBin = ReadCluster['instance_binaries']
        serDat = ReadCluster['server_datadir']
        

    # get cluster info
    global CompIp, CompPwd, CompPort, CompDir, CompUser
    
    CompIp, CompPwd, CompPort, CompDir, CompUser = [], [], [], [], []

    for i in CompTotal: # get computing node info
        ip=i['ip']
        port=i['port']
        #datadir=i['datadir']
        user=i['user']
        pwd=i['password']
        CompPwd.append(pwd)
        CompIp.append(ip)
        CompPort.append(port)
        #CompDir.append(datadir)
        CompUser.append(user)
        if types == 'one_click':
            datadir=i['datadir']
            CompDir.append(datadir)

    try:
        OpenConf=open(config,encoding='utf-8') # get computing conf info
        ReadConf=json.loads(OpenConf.read())
    except:
        print="========================================================================"
        print("\n\n%s\n--------- open configuration file %s fail, please check --------\n%s\n" % (printe, config,printe))
    finally:
        pass
    
    global Compkeys, Compvalues, Medakeys, Medavalues, Datakeys, Datavalues

    CompConf=ReadConf['comp'][0] # get data&metadata conf info
    MedaConf=ReadConf['metadata'][0]
    DataConf=ReadConf['storage'][0]

    Compkeys=list(CompConf.keys())
    Compvalues=list(CompConf.values())
    Medakeys=list(MedaConf.keys())
    Medavalues=list(MedaConf.values())
    Datakeys=list(DataConf.keys())
    Datavalues=list(DataConf.values())
    global CompNum, sCompNum, MedaNum, DataNum
    CompNum=len(Compkeys)
    sCompNum = str(CompNum)
    MedaNum=len(Medakeys)
    DataNum=len(Datakeys)


    try:
        os.remove('config.sh')
    except:
        pass
    finally:
        pass

def pgconn(host, port, user, pwd, sql):
    global lists
    conn = psycopg2.connect(database = 'postgres', user = user, host = host, port = port, password = pwd)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(sql)
    lists = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()

def wFile(stmt):
    of=open('config.sh','a')
    of.write("#%s\n\n" % (stmt))
    of.close()

def WFile(stmt, es):
    of=open('config.sh','a')
    if es == 'y':
        of.write("echo %s\n" % (stmt))
    elif es == 'n':
        of.write('%s\n\n' % (stmt))
        of.write("")
    of.close()

def myconn(host, port, sql):
    conn = pymysql.connect(host = host, user = "pgx",port = int(port), password = "pgx_pwd", database = "mysql")
    cursor = conn.cursor()
    cursor.execute(sql)
    cursor.close()
    conn.close()

def varPort():
    global port
    port = []
    for row in lists:
        srow = (str(row))
        srow = srow.replace('(','')
        srow = srow.replace(',)','')
        srow = int(srow)
        port.append(srow)

def varHost():
    global host
    host = []
    for row in lists:
        srow = (str(row))
        srow = srow.replace('\'','')
        srow = srow.replace('(','')
        srow = srow.replace(',)','')
        host.append(srow)

def chInfo(stmt):
    stmt = '\n========================================================================\nsetting %s...\n========================================================================\n'% (stmt)
    print(stmt)

def configs():
    
    # setting computing node ========================================================================
    CIPN = 0
    for i in CompIp:
        for a in range(0, CompNum):
            if Compvalues[a] :
                SCompkeys = ''.join(Compkeys[a])
                if types == 'one_click':
                    SCompDir = ''.join(CompDir[CIPN])
                SCompvalues = str(Compvalues[a])
                SCompIp = ''.join(CompIp[CIPN])
                SCompPort = str(CompPort[CIPN])
                
                num = 0
                if types == 'one_click':
                    BashStmt = "ssh %s@%s \'echo %s = %s >> %s/postgresql.conf\'" % (defuser, SCompIp, SCompkeys, SCompvalues, SCompDir)
                    print(BashStmt)
                    
                elif types == 'xpenal':
                    #/home/kunlun/testmgr0.9.2/server_datadir/instance_data/comp_datadir/57030/postgresql.conf
                    BashStmt = "ssh %s@%s \'echo %s = %s >> %s/server_datadir/instance_data/comp_datadir/%s/postgresql.conf\'" % (defuser, SCompIp, SCompkeys, SCompvalues, defbase, SCompPort)
                    num = num + 1
                
                elif types == 'cluster_mgr':
                    BashStmt = "ssh %s@%s \'echo %s = %s >> %s/%s/postgresql.conf\'" % (defuser, SCompIp, SCompkeys, SCompvalues, serDat, SCompPort)
                    num = num + 1

                WFile(BashStmt, 'y')
                WFile(BashStmt, 'n')
            
            else:
                err = 'Computing node' + SCompIp + ':' + SCompPort + 'parameter :"' + SCompkeys + '" values is null'
                print(err)

        if types == 'one_click':
            stmt = "ssh %s@%s \'%s/kunlun-server-0.9.2/bin/pg_ctl reload -D %s\'" % (defuser, SCompIp, defbase, SCompDir)
        
        elif types == 'xpenal':
            #/home/kunlun/testmgr0.9.2/instance_binaries/computer/57030/kunlun-server-0.9.2/bin/pg_ctl
            stmt = "ssh %s@%s \'%s/instance_binaries/computer/%s/kunlun-server-0.9.2/bin/pg_ctl reload -D %s/server_datadir/instance_data/comp_datadir/%s\'" % (defuser, SCompIp, defbase, SCompPort, defbase, SCompPort) 

        elif types == 'cluster_mgr':
            stmt = "ssh %s@%s \'%s/%s/kunlun-server-0.9.2/bin/pg_ctl reload -D %s/%s\'" % (defuser, SCompIp, insBin, SCompPort, serDat, SCompPort)

        WFile(stmt, 'y')
        WFile(stmt, 'n')
        CIPN+=1

    #setting Metadata nodes ========================================================================
    chInfo('Metadatas')
    n = 0
    for i in Medakeys:
        hostSql = 'select hostaddr from pg_cluster_meta_nodes'
        portSql = 'select port from pg_cluster_meta_nodes'

        pgconn(CompIp[0], CompPort[0], CompUser[0], CompPwd[0], portSql)
        varPort()
        pgconn(CompIp[0], CompPort[0], CompUser[0], CompPwd[0], hostSql)
        varHost()

        num = 0
        for hosts in host:
            stmt = 'set global %s = %s' % (i, str(Medavalues[n]))
            wf = 'mysql -h %s -P %s -upgx -ppgx_pwd "%s"' % (hosts, port[num], stmt)
            print(wf)
            myconn(hosts, port[num], stmt)
            wFile(wf)
            num = num + 1

        n = n + 1
    
    chInfo('Datanodes')
    #setting Datanodes ========================================================================
    n = 0
    for i in Datakeys:
        hostSql = 'select hostaddr from pg_shard_node'
        portSql = 'select port from pg_shard_node'
        pgconn(CompIp[0], CompPort[0], CompUser[0], CompPwd[0], portSql)
        varPort()
        pgconn(CompIp[0], CompPort[0], CompUser[0], CompPwd[0], hostSql)
        varHost()
        num = 0
        for hosts in host:
            stmt = 'set global %s = %s' % (i, str(Datavalues[n])) 
            wf = 'mysql -h %s -P %s -upgx -ppgx_pwd "%s"' % (hosts, port[num], stmt)
            print(wf)
            myconn(hosts, port[num], stmt)
            wFile(wf)

            num = num + 1

        n = n + 1

    chInfo('computing nodes')
    subprocess.run("bash ./config.sh",shell=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Configure')
    parser.add_argument('--defuser', type=str, default='kunlun', help='User')
    parser.add_argument('--defbase', type=str, default='/kunlun', help='basedir, 如果是通过cluster_mgr直接安装的则不用传该参数')
    parser.add_argument('--install', type=str, default='./install.json', help='The original configuration file for the Kunlun_cluster')
    parser.add_argument('--config', type=str, default='./configure.json', help='the configuration file')
    parser.add_argument('--type', type = str, default='one_click', help = 'can be "one_click" or "cluster_mgr" or "xpenal", "one_click" 是用的一键脚本安装的集群，"cluster_mgr"是用的cluster_mgr安装的集群,"xpenal"就是通过xpenal安装的集群')
    args = parser.parse_args()
    print (args)

    defuser = args.defuser
    defbase = args.defbase
    install = args.install
    config = args.config
    types = args.type
    readJsonFile()
    configs()

