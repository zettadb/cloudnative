#这个是用来发送api的脚本，包括修改文件

# 编写配置文件
metaPriHost=`cat configure.txt | grep /self/hosts/meta_data_node/ | grep /ip | awk '{print $2}'`
shardNum=`cat ~/configure.txt | grep /self/hosts/data_node/ | grep /gid  | awk '{print $2}' | sort | uniq | tail -1`
echo 'MetaPrimaryNode:' > /home/kunlun/config.yaml
echo "  host: \"$metaPriHost\"" >> /home/kunlun/config.yaml
echo "  port: \"6001\"" >> /home/kunlun/config.yaml
echo 'computer:' >> /home/kunlun/config.yaml
for i in `cat ~/configure.txt | grep /self/hosts/computing_node/ | grep /ip | awk '{print $2}'`; do echo "  - $i" >> /home/kunlun/config.yaml; done
echo 'storage:' >> /home/kunlun/config.yaml
for i in `cat ~/configure.txt | grep /self/hosts/data_node | grep /ip | awk '{print $2}'`; do echo "  - $i" >> /home/kunlun/config.yaml; done
        #sed -i 's/|//g' /home/kunlun/config.yaml
maxGid=`cat configure.txt | grep /self/hosts/data | grep gid | awk '{print $2}' | sort -n | uniq | tail -1`
maxSid=`cat configure.txt | grep /self/hosts/data | grep /sid | awk '{print $2}' | sort -n | uniq | tail -1`
dataNodeNum=`echo "scale=0;$maxSid/$maxGid" | bc -l`
compNodeNum=`cat configure.txt | grep /self/hosts/computing_node/  | grep role | wc -l`
dataCpu=`cat configure.txt | grep /cpu | grep -v cpu_model | grep self/hosts/data_node | awk '{print $2}' | uniq`
dataMem=`cat configure.txt | grep memory | grep self/hosts/data_node | awk '{print $2}' | uniq`
echo "shards: $shardNum" >> /home/kunlun/config.yaml
echo "nodes: $dataNodeNum" >> /home/kunlun/config.yaml
echo "comps: $compNodeNum" >> /home/kunlun/config.yaml
echo "total_mem: $dataMem" >> /home/kunlun/config.yaml
echo "total_cpu_cores: $dataCpu" >> /home/kunlun/config.yaml
cat << EOF >> /home/kunlun/config.yaml
pgsql_port_range: "5431-7000"
mysql_port_range: "8000-10000"
ha_mode: "rbr"
dbcfg: 0
user_name: "kunlun"
datadir: "/home/kunlun/base/storage_datadir"
logdir: "/home/kunlun/base/storage_logdir"
wal_log_dir: "/home/kunlun/base/storage_waldir"
comp_datadir: "/home/kunlun/base/server_datadir"
nick_name: "cluster1"
max_storage_size: 20
max_connections: 1000
innodb_size: 1
fullsync_level: 1
EOF

#运行发送api脚本
cd /home/kunlun/cluster_mgr_sc
python3 install_cluster.py --config /home/kunlun/config.yaml --type install

