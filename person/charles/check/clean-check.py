import json
import subprocess
from time import sleep
import argparse
import threading

def readJsonFile():
    f = open(File, encoding = 'utf-8')
    fload = json.loads(f.read())
    cluster = fload['cluster']
    meta = cluster['meta']['nodes']
    data = cluster['data']

    global metaport, metadir, dataport, datadir, metaip, dataip, allhost, ahost
    metaport, metadir, dataport, datadir, metaip, dataip = [], [], [], [], [], []

    for i in meta:
        Metaport = i['port']
        Metadir = i["log_dir_path"]
        Metaip = i["ip"]
        metaport.append(Metaport)
        metadir.append(Metadir)
        metaip.append(Metaip)

    for i in data:
        for a in i["nodes"]:
            Dataport = a["port"]
            Datadir = a["log_dir_path"]
            Dataip = a["ip"]
            dataip.append(Dataip)
            dataport.append(Dataport)
            datadir.append(Datadir)

    allhost=[]
    allhost.extend(metaip)
    allhost.extend(dataip)
    ahost = list(set(allhost))

def clean(ip, path):
    stmt = 'ssh ' + defuser + '@' + ip + " 'cd " + path + " && for i in `ls | sed \"$\"d | sed \"$\"d | sed \"$\"d`; do echo $i; rm $i; done'"
    subprocess.run(stmt, shell=True)
    print(stmt)

def check(ip):
    stmt1 = 'ssh ' + defuser + '@' + ip + " 'date && iostat' >> ./check/io-" + ip + '.sh'
    stmt2 = 'ssh ' + defuser + '@' + ip + " 'date && free' >> ./check/men-" + ip + '.sh'
    stmt3 = 'ssh ' + defuser + '@' + ip + " 'sar -n DEV 1 1 | grep -A 2 IFACE' >> ./check/net-" + ip + '.sh'
    stmt4 = 'ssh ' + defuser + '@' + ip + " 'sar 1 1' >> ./check/cpu-" + ip + '.sh'

    print(stmt1 + ' ======>> '  + stmt2 + ' ======> '  + stmt3+ ' ======> ' + stmt4)
    subprocess.run(stmt1, shell=True)
    subprocess.run(stmt2, shell=True)
    subprocess.run(stmt3, shell=True)
    subprocess.run(stmt4, shell=True)

def iostat(ip):
    stmt1 = 'ssh ' + defuser + '@' + ip + " 'date && iostat' >> ./check/io-" + ip + '.sh'
    print(stmt1)
    subprocess.run(stmt1, shell=True)

def free(ip):
    stmt2 = 'ssh ' + defuser + '@' + ip + " 'date && free' >> ./check/men-" + ip + '.sh'
    print(stmt2)
    subprocess.run(stmt2, shell=True)

def net(ip):
    stmt3 = 'ssh ' + defuser + '@' + ip + " 'sar -n DEV 1 1 | grep -A 2 IFACE' >> ./check/net-" + ip + '.sh'
    print(stmt3)
    subprocess.run(stmt3, shell=True)

def cpu(ip):
    stmt4 = 'ssh ' + defuser + '@' + ip + " 'sar 1 1' >> ./check/cpu-" + ip + '.sh'
    print(stmt4)
    subprocess.run(stmt4, shell=True)

def checkThread(ip):
    t1 = threading.Thread(target = iostat, args=(ip,))
    t2 = threading.Thread(target = free, args=(ip,))
    t3 = threading.Thread(target = net, args=(ip,))
    t4 = threading.Thread(target = cpu, args=(ip,))
    t1.start()
    t2.start()
    t3.start()
    t4.start()

def all():
    n=0
    for i in metaip:
        path = metadir[n] + '/' + str(metaport[n]) + '/dblogs/bin'
        clean(i, path)
        n = n + 1

    n = 0
    for i in dataip:
        path = datadir[n] + '/' + str(dataport[n]) + '/dblogs/bin'
        clean(i, path)
        n = n + 1

    num = 0
    while True:
        
        for i in ahost:
            #check(i)
            checkThread(i)

        num = num + 1
        
        print(num)
        while num == 360 :
            n = 0
            for i in metaip:
                path = metadir[n] + '/' + str(metaport[n]) + '/dblogs/bin'
                clean(i, path)
                n = n + 1
            
            n = 0
            for i in dataip:
                path = datadir[n] + '/' + str(dataport[n]) + '/dblogs/bin'
                clean(i, path)
                n = n + 1

            print('\n========\nnow clean\n========\n')

            num = 0
        sleep(10)

if __name__ == '__main__':
    ps = argparse.ArgumentParser(description='check cluster healthy && clean each datanode binlog with 1 hour')
    ps.add_argument('--config', default='install.json', type=str, help='the configuration json file with Kunlun_cluster')
    ps.add_argument('--defuser', default='kunlun', type=str, help='default user with Kunlun_cluster')
    args=ps.parse_args()
    print(args)
    File = args.config
    defuser = args.defuser
    readJsonFile()
    all()
