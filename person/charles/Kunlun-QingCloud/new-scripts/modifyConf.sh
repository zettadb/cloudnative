cd /home/kunlun
selfRole=`cat /home/kunlun/configure.txt | grep /self/host/role | awk '{print $2}'`
serDir=/home/kunlun/base/server_datadir/5432/postgresql.conf
stoDir=/home/kunlun/base/storage_datadir/8001/data/8001.cnf
serNum=`cat /home/kunlun/configure.txt | grep /self/hosts/computing_node | grep /sid | wc -l`

if [[ "$selfRole" == "computing_node" ]]
then
	if [[ -e '/home/kunlun/base/first' ]]
	then
		for i in max_connections  shared_buffers temp_buffers log_min_duration_statement statement_timeout mysql_connect_timeout mysql_read_timeout mysql_write_timeout
		do
			sed -i '$d' $serDir
		done
	else
		touch /home/kunlun/base/first
	fi

	for i in max_connections  shared_buffers temp_buffers log_min_duration_statement statement_timeout mysql_connect_timeout mysql_read_timeout mysql_write_timeout
	do
		values=`cat configure.txt | grep /self/env/$i | awk '{print $2}'`
		echo "$i: $values" >> $serDir
	done

	cd /home/kunlun/base/instance_binaries/computer/5432/kunlun-server-1.0.1/bin
	./pg_ctl -D /home/kunlun/base/server_datadir/5432 reload

elif [[ "$selfRole" == "meta_data_node" ]]
then

# 配置install_xa.json文件
	cat << EOF > /home/kunlun/configure/install_xc.json
{
    "instance_binaries":"/home/kunlun/base/instance_binaries/computer",
    "server_datadir":"/home/kunlun/base/server_datadir",
    "cluster":{
        "comp":{
            "nodes":[
                {
EOF
	for i in `cat configure.txt | grep /self/hosts/computing_node | grep /ip | awk '{print $2}'`
	do
		cat << EOF >>/home/kunlun/configure/install_xc.json
                    "ip":"192.168.0.132",
                    "port":8881,
                    "user":"pwd2",
                    "password":"pwd2"
                },
                {
EOF
	done

sed -i '$d' /home/kunlun/configure/install_xc.json && sed -i '$d' /home/kunlun/configure/install_xc.json
	cat << EOF >> /home/kunlun/configure/install_xc.json
                }
            ]
        }
    }
}

EOF

#配置 configure.json 文件
	cat << EOF > /home/kunlun/configure/configure.json
{
        "comp":[{
                        "statement_timeout":1000000,
                        "mysql_read_timeout":1000000,
                        "mysql_write_timeout":1000000,
                        "lock_timeout":1000000,
                        "log_min_duration_statement":1000000
                }

        ],

        "metadata":[{
EOF
	for i in lock_timeout innodb_lock_wait_timeout lock_wait_timeout
	do
		values=`cat configure.txt | grep /self/env/$i | awk '{print $2}'`
		cat << EOF >> /home/kunlun/configure/configure.json
                        "$i":$values
EOF
	done

	cat << EOF >> /home/kunlun/configure/configure.json
                }
        ],
        "storage":[{
EOF

	for i in lock_timeout innodb_lock_wait_timeout lock_wait_timeout
        do
                values=`cat configure.txt | grep /self/env/$i | awk '{print $2}'`
                cat << EOF >> /home/kunlun/configure/configure.json
                        "$i":values
EOF
	done

	cat << EOF >> /home/kunlun/configure/configure.json
                }
        ]
}
EOF

#运行脚本
	cd /home/kunlun/configure/
	python3 configure.py --defuser kunlun --install install_xc.json --config configure.json --component storage
fi
