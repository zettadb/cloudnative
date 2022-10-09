
role=$1
ip=$2
groupSeeds=$3
clusterSeeds=$4
if [[ "$role" == "meta" ]]
then
#生成 mysql_meta.json
        cat << EOF > conf/mysql_meta.json
{
    "ha_mode": "mgr",
    "nodes": [
        {
EOF
echo $ip

        for i in $ip
        do
		echo $i
                cat << EOF >> conf/mysql_meta.json
            "is_primary": false,
            "ip": "$i",
            "port": 6001,
            "xport": 60010,
            "mgr_port": 60011,
            "innodb_buffer_pool_size": "64MB",
            "election_weight": 50,
            "data_dir_path": "/home/kunlun/base/storage_datadir/6001",
            "log_dir_path": "/home/kunlun/base/storage_logdir/6001",
            "innodb_log_dir_path": "/home/kunlun/base/storage_waldir/6001",
            "program_dir": "/home/kunlun/base/instance_binaries/storage/6001",
            "user": "kunlun"
        },
        {

EOF

        done
        sed -i '$d' conf/mysql_meta.json && sed -i '$d' conf/mysql_meta.json && sed -i '$d' conf/mysql_meta.json
        cat << EOF >> conf/mysql_meta.json
        }
    ],
    "group_seeds": "$groupSeeds",
    "group_uuid": "8891a8ce-156a-11ed-b6af-7c10c93f0c7e"
}
EOF
	sed -i '0,/false/{s/false/true/}' conf/mysql_meta.json

#生成reg_meta.json
	cat << EOF > conf/reg_meta.json
[
    {
EOF
	for i in $ip
	do
		cat << EOF >> conf/reg_meta.json
        "is_primary": true,
        "data_dir_path": "/home/kunlun/base/storage_datadir/6001",
        "user": "pgx",
        "nodemgr_bin_path": "/home/kunlun/base/kunlun-node-manager-1.0.1/bin",
        "ip": "$i",
        "password": "pwd3",
        "port": 6001
    },
    {
EOF
	done
	sed -i '$d' conf/reg_meta.json && sed -i '$d' conf/reg_meta.json &&
	cat << EOF >> conf/reg_meta.json    
    }
]
EOF
	sed -i '0,/false/{s/false/true/}' conf/reg_meta.json
## ======== cluster +++++++++
elif [[ "$role" == "cluster" ]]
then
	echo i am cluster
	#cat << EOF >> /home/kunlun/base/kunlun-cluster-manager-1.0.1/conf/cluster_mgr.cnf
	cat << EOF >> ./base/kunlun-cluster-manager-1.0.1/conf/cluster_mgr.cnf
meta_group_seeds = $groupSeeds
brpc_raft_port = 56001
brpc_http_port = 56000
local_ip = $ip
raft_group_member_init_config = $clusterSeeds
prometheus_path = /home/kunlun/base/program_binaries/prometheus
prometheus_port_start = 56010
EOF
## ======== node +++++++++
elif [[ "$role" == "node" ]]
then
	echo i am node
	cat << EOF >> ./base/kunlun-node-manager-1.0.1/conf/node_mgr.cnf
meta_group_seeds = $groupSeeds
brpc_http_port = 56002
nodemgr_tcp_port = 56003
local_ip = $ip
program_binaries_path = /home/kunlun/base/program_binaries
instance_binaries_path = /home/kunlun/base/instance_binaries
prometheus_path = /home/kunlun/base/program_binaries/prometheus
storage_prog_package_name = kunlun-storage-1.0.1
computer_prog_package_name = kunlun-server-1.0.1
prometheus_port_start = 56020
EOF
fi
