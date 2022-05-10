import subprocess
from time import sleep
import json
import argparse
import os
import psycopg2

def readJsonFile():
    OpenCluster=open(install, encoding='utf-8')
    ReadCluster=json.loads(OpenCluster.read())

    MetaTotal=ReadCluster['cluster']['meta']['nodes']
    CompTotal=ReadCluster['cluster']['comp']['nodes']
    DataTotal=ReadCluster['cluster']['data']

    # get cluster info
    global MetaIp, MetaPort, MetaDir, CompIp, CompPwd, MetaUser, CompPort, CompDir, CompUser, DataIp, DataPort, DataDir, DataUser
    
    MetaIp, MetaPort, MetaDir, CompIp, CompPwd, MetaUser, CompPort, CompDir, CompUser, DataIp, DataPort, DataDir, DataUser = [], [], [], [], [], [], [], [], [], [], [], [], []

    for i in MetaTotal: #get metadata node info
        ip=i['ip']
        port=i['port']
        datadir=i['data_dir_path']
        user=i['user']
        MetaIp.append(ip)
        MetaPort.append(port)
        MetaDir.append(datadir)
        MetaUser.append(user)
        

    for i in CompTotal: # get computing node info
        ip=i['ip']
        port=i['port']
        datadir=i['datadir']
        user=i['user']
        pwd=i['password']
        CompPwd.append(pwd)
        CompIp.append(ip)
        CompPort.append(port)
        CompDir.append(datadir)
        CompUser.append(user)

    for i in DataTotal: # get data node info
        for a in i['nodes']:
            ip=a['ip']
            port=a['port']
            datadir=a['data_dir_path']
            user=a['user']
            DataIp.append(ip)
            DataPort.append(port)
            DataDir.append(datadir)
            DataUser.append(user)

    try:
        OpenConf=open(config,encoding='utf-8') # get computing conf info
        ReadConf=json.loads(OpenConf.read())
    except:
        printe="========================================================================"
        print("\n\n%s\n--------- open configuration file %s fail, please check --------\n%s\n" % (printe, config,printe))
    finally:
        pass
    
    global Compkeys, Compvalues, Medakeys, Medavalues

    CompConf=ReadConf['comp'][0] # get data&metadata conf info
    MedaConf=ReadConf['meta-storage'][0]

    Compkeys=list(CompConf.keys())
    Compvalues=list(CompConf.values())
    Medakeys=list(MedaConf.keys())
    Medavalues=list(MedaConf.values())
    global CompNum, sCompNum, MedaNum
    CompNum=len(Compkeys)
    sCompNum = str(CompNum)
    MedaNum=len(Medakeys)

    try:
        os.remove('config.sh')
    except:
        pass
    finally:
        pass

def configs():
    CIPN = 0
    for i in CompIp:
        for a in range(0, CompNum):
            if Compvalues[a] :
                SCompkeys = ''.join(Compkeys[a])
                SCompDir = ''.join(CompDir[CIPN])
                SCompvalues = str(Compvalues[a])
                SCompUser = ''.join(MetaUser[CIPN])
                SCompIp = ''.join(CompIp[CIPN])
                SCompPort = str(CompPort)
                
                of=open('config.sh','a')
                '''
                AddLine = "line=`cat %s/postgresql.conf | awk -F= '\\'{print \\$1}\\'' | grep -n -w '\\'^%s\\'' | awk -F: '\\'{print \\$1}\\''` && " % (SCompDir,SCompkeys)
                SedDel = 'sed -i "${line}d" ' + SCompDir +'/postgresql.conf && '
                SedAdd = 'sed -i "${line}i ' + SCompkeys + ' = ' + SCompvalues + '" ' + SCompDir +'/postgresql.conf'
                BashStmt = AddLine + SedDel + SedAdd
                '''
                BashStmt = 'echo %s = %s > %s/postgresql.conf' % (SCompvalues, SCompkeys, SCompDir )
                of.write("ssh %s@%s '%s'\n\necho ssh %s@%s '%s'\n\n" %(defuser, SCompIp, BashStmt, defuser, SCompIp, BashStmt))
                of.write("")
                of.close()
            else:
                err = 'Computing node' + SCompIp + ':' + SCompPort + 'parameter :"' + SCompkeys + '" values is null'
                print(err)

        of=open('config.sh','a')
        stmt = "ssh %s@%s '%s/kunlun-server-0.9.1/bin/pg_ctl reload -D %s'\n\necho ssh %s@%s '%s/kunlun-server-0.9.1/bin/pg_ctl reload -D %s'\n\n" % (defuser, SCompIp, defbase, SCompDir, defuser, SCompIp, defbase, SCompDir)
        of.write(stmt)
        of.close()

        CIPN+=1

    MIPN = 0
    for i in MetaIp:
        for a in range(0, MedaNum):
            if Medavalues[a]:
                SMedakeys = ''.join(Medakeys[a])
                SMedavalues = str(Medavalues[a])
                SMetaIp = ''.join(MetaIp[MIPN])
                SMetaPort = str(MetaPort[MIPN])
                SMetaDir = ''.join(MetaDir[MIPN])
                of=open('config.sh','a')
                '''
                AddLine = "line=`cat %s/%s/my_%s.cnf | awk -F= '\\'{print \\$1}\\'' | grep -n -w '\\'^%s\\'' | awk -F: '\\'{print \\$1}\\''` && " % (SMetaDir, SMetaPort, SMetaPort, SMedakeys)
                SedDel = 'sed -i "${line}d" ' + SMetaDir +'/' + SMetaPort + '/my_' + SMetaPort +'.cnf && '
                SedAdd = 'sed -i "${line}i ' + SMedakeys + ' = ' + SMedavalues + '" ' + SMetaDir +'/' + SMetaPort + '/my_' + SMetaPort +'.cnf '
                BashStmt = AddLine + SedDel + SedAdd
                '''
                BashStmt = 'echo %s = %s > %s/%s/my_%s.conf' % (SMedakeys, SMedavalues, SMetaDir, SMetaPort, SMetaPort)
                of.write("ssh %s@%s '%s'\n\necho ssh %s@%s '%s'\n\n" %(defuser, SMetaIp, BashStmt, defuser, SMetaIp, BashStmt))
                of.close()
            else:
                err = 'Metadata node' + SMetaIp + ':' + SMetaPort + 'parameter :"' + SMedakeys + '" vaules is null! '
                print(err)


        MIPN+=1

    DIPN = 0
    for i in DataIp:
        for a in range(0, MedaNum):
            if Medavalues[a]:
                SMedakeys = ''.join(Medakeys[a])
                SMedavalues = str(Medavalues[a])
                SDataIp = ''.join(DataIp[DIPN])
                SDataPort = str(DataPort[DIPN])
                SDataDir = ''.join(DataDir[DIPN])

                of=open('config.sh','a')
                '''
                AddLine = "line=`cat  %s/%s/my_%s.cnf | awk -F= '\\'{print \\$1}\\'' | grep -n -w '\\'^%s\\'' | awk -F: '\\'{print \\$1}\\''` && " % (SDataDir, SDataPort, SDataPort, SMedakeys)
                SedDel = 'sed -i "${line}d" ' + SDataDir +'/' + SDataPort + '/my_' + SDataPort +'.cnf && '
                SedAdd = 'sed -i "${line}i ' + SMedakeys + ' = ' + SMedavalues + '" ' + SDataDir +'/' + SDataPort + '/my_' + SDataPort +'.cnf '
                BashStmt = AddLine + SedDel + SedAdd
                '''
                BashStmt = 'echo %s = %s > %s/%s/my_%s.conf' % (SMedakeys, SMedavalues, SDataDir, SDataPort, SDataPort)
                of.write("ssh %s@%s '%s'\n\necho ssh %s@%s '%s'\n\n" %(defuser, SDataIp, BashStmt, defuser, SDataIp, BashStmt))
                of.close()
            else:
                err = 'Data node' + SDataIp + ':' + SDataPort + 'parameter :"' + SMedakeys + '" values is null!'
                print(err)

        DIPN+=1

    n = 0
    for i in Medakeys:
        stmt = 'set shard global ' + i + ' = ' + str(Medavalues[n])
        print(stmt)
        of=open('config.sh','a')
        of.write("#%s\n\n" % (stmt))
        of.close()
        conn = psycopg2.connect(database = 'postgres', user = CompUser[0], host = CompIp[0], port = CompPort[0], password = CompPwd[0])
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(stmt)
        conn.commit()
        cur.close()
        conn.close()
        n = n + 1

    #subprocess.run("bash ./config.sh",shell=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Configure')
    parser.add_argument('--defuser', type=str, default='kunlun', help='User')
    parser.add_argument('--defbase', type=str, default='/kunlun', help='basedir')
    parser.add_argument('--install', type=str, default='./install.json', help='The original configuration file for the Kunlun_cluster')
    parser.add_argument('--config', type=str, default='./configure.json', help='the configuration file')

    args = parser.parse_args()
    print (args)

    defuser=args.defuser
    defbase=args.defbase
    install=args.install
    config=args.config
    readJsonFile()
    configs()

