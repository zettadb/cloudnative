
rm -rf conf && mkdir conf
nets=`cat /etc/confd/confd.toml  | grep nodes | awk -F= '{print $2}' | sed 's/^...//' | sed 's/..$//'`
curl $nets > configure.txt
compIp=`cat configure.txt | grep /self/hosts/computing_node/ | grep /ip | awk '{print $2}'`
dataIp=`cat configure.txt | grep /self/hosts/data_node/ | grep /ip | awk '{print $2}'`
dataGid=`cat configure.txt | grep /self/hosts/data_node/ | grep /gid | awk '{print $2}'`
dataRepIp=`cat configure.txt | grep /self/hosts/data_node-replica/ | grep /ip | awk '{print $2}'`
dataRepGid=`cat configure.txt | grep /self/hosts/data_node-replica/ | grep /gid | awk '{print $2}'`
metaIp=`cat configure.txt | grep /self/hosts/meta_data_node/ | grep /ip | awk '{print $2}'`
metaRepIp=`cat configure.txt | grep /self/hosts/meta_data_node-replica/ | grep /ip | awk '{print $2}'`
selfRole=`cat configure.txt | grep /self/host/role | awk '{print $2}'`
selfIp=`cat configure.txt | grep /self/host/ip | awk '{print $2}'`
#for i in $compIp; do echo comp: $i; done
#for i in $dataIp; do echo data: $i; done
#echo $dataGid
#for i in $dataRepIp; do echo dataRep: $i; done
#echo $dataRepGid
#for i in $metaIp; do echo meta: $i; done
#for i in $metaRepIp; do echo metaRep: $i; done
#echo i am $selfRole and my ip is $selfIp

# 产生对应的配置文件

# data节点配置文件
for i in $dataGid
do
	masterId=`cat configure.txt | grep "$i"$ | grep /self/hosts/data_node/ | grep gid | awk -F/ '{print $5}'`
	master_dataip=`cat configure.txt | grep "$masterId" | grep /self/hosts/data_node/ | grep /ip | awk '{print $2}'`
	repDataGId=`echo $dataRepGid | grep "$i"$ | grep /self/hosts/data_node-replica/ | grep gid | awk -F/ '{print $5}'`
	echo -en \"group_seeds\": \"$master_dataip:6001 >> conf/data${i}seed.txt
	echo -e mas: $master_dataip >> conf/data${i}.txt
	#echo -n "$master_dataip" >> conf/dataIp${i}.txt
	
	for m in `cat configure.txt | grep "$i"$ | grep /self/hosts/data_node-replica/ | grep gid | awk -F/ '{print $5}'`
	do
		rep_dataip=`cat configure.txt | grep "$m" | grep /self/hosts/data_node-replica/ | grep /ip | awk '{print $2}'`
		echo -n ,$rep_dataip:6001 >> conf/data${i}seed.txt
		echo -e rep: $rep_dataip >> conf/data${i}.txt
		echo -n " $rep_dataip" >> conf/dataIp${i}.txt
	done
	
	echo -n \" >> conf/data${i}seed.txt
done

# meta 节点配置文件
rm -rf conf/meta.txt
echo $metaIp >> conf/meta.txt
echo -en $metaIp >> conf/metaSeed.txt
echo -en $metaIp:6001 >> conf/metaClusterSeed.txt
for i in `cat configure.txt | grep /self/hosts/meta_data_node-replica/ | grep /ip | awk '{print $2}'`
do
	echo $i >> conf/meta.txt
	echo -n " $i" >> conf/metaIp.txt
	echo -n " $i" >> conf/metaSeed.txt
	echo -n ",$i:6001" >> conf/metaClusterSeed.txt
done 

# comp 节点配置文件
rm -rf conf/data.txt
for i in `cat configure.txt | grep /self/hosts/computing_node/ | grep /ip | awk '{print $2}'`
do
	echo $i >> conf/comp.txt
	echo -n $i >> conf/compIp.txt
done

# cluster_mgr 配置文件
echo -en $metaIp:56001:0 >> conf/clusterSeed.txt
for i in `cat configure.txt | grep /self/hosts/meta_data_node-replica/ | grep /ip | awk '{print $2}'`
do
	echo -n ",$i:56001:0" >> conf/clusterSeed.txt
done

#clusterMetaSeeds=`cat conf/metaClusterSeed.txt`

if [[ "$selfRole" == "meta_data_node"  ]]
then
	# 生成mysql_meta.json文件
	metaseeds=`cat conf/metaSeed.txt`
	echo metaseeds = $metaseeds
	metaIpR=`cat conf/metaIp.txt`
	echo metaIpR = $metaIpR
	/bin/bash change_conf.sh meta "$metaseeds" "$metaIpR"
	
	# 修改cluster_mgr配置文件
	clusterSeeds=`cat conf/clusterSeed.txt`
	echo `cat conf/clusterSeed.txt`
	clusterMetaSeeds=`cat conf/metaClusterSeed.txt`
	/bin/bash change_conf.sh cluster $selfIp "$clusterMetaSeeds" "$clusterSeeds"
	
	# 修改node_mgr配置文件
	/bin/bash change_conf.sh node $selfIp "$clusterMetaSeeds"

	#安装 -- bootstarp
	cd /home/kunlun/base/program_binaries/kunlun-storage-1.0.1/dba_tools
	python2 install-mysql.py --config=/home/kunlun/conf/mysql_meta.json --target_node_index=0 --cluster_id=meta --shard_id=meta --server_id=1 --ha_mode=mgr
	a=`echo $?`
	cd /home/kunlun
	for i in `cat configure.txt | grep /self/hosts/meta_data_node-replica/ | grep /ip | awk '{print $2}'`; do bash send_ready.sh $i metaReady; done
	cd /home/kunlun/base/kunlun-cluster-manager-1.0.1/bin
	bash start_cluster_mgr.sh </dev/null >& start.log & 
	#cd /home/kunlun/base/kunlun-node-manager-1.0.1/bin
	#bash start_node_mgr.sh </dev/null >& start.log &
	
	cd /home/kunlun
	#for i in `cat /home/kunlun/configure.txt | grep /self/hosts/meta_data_node-replica | grep /ip | awk '{print $2}'`; do python3 check.py --host $i --type mysql; a=`echo $?`; while [[ "$a" != "0" ]]; do python3 check.py --host $i --type mysql; a=`echo $?`; echo wait 1s...; sleep 1;  echo -e "meta cluster install\n"; done; done
	a=1
	for i in `cat configure.txt | grep /self/hosts/meta_data_node-replica/ | grep /ip | awk '{print $2}'`; do while [[ "$a" == "1" ]]; do if [[ ! -f "${i}metaRepReady" && ! -f "repNoready" ]]; then a=1;echo $a; sleep 1; else a=0; fi; done; sleep 5; done
	sleep 5
	
	cd /home/kunlun/base/program_binaries/kunlun-server-1.0.1/scripts/
	python2 bootstrap.py --config=/home/kunlun/conf/reg_meta.json --bootstrap_sql=/home/kunlun/base/program_binaries/kunlun-server-1.0.1/scripts/meta_inuse.sql --ha_mode=mgr
	a=`echo $?`
	if [[ $a == "0" ]] ; then for i in `cat /home/kunlun/configure.txt | grep /self/hosts | grep /ip | awk '{print $2}'` ; do cd /home/kunlun; bash ./send_ready.sh $i ready; done; else for i in `cat /home/kunlun/configure.txt | grep /self/hosts | grep /ip | awk '{print $2}'` ; do cd /home/kunlun; bash ./send_ready.sh $i noready; done; sleep 10; exit 1; fi
	cd /home/kunlun/base/program_binaries/kunlun-storage-1.0.1/dba_tools/
	bash ./imysql.sh 6001 < /home/kunlun/dba_tools_db.sql
	cd /home/kunlun/base/kunlun-cluster-manager-1.0.1/bin && /bin/bash restart_cluster_mgr.sh </dev/null >& start.log &
	cd /home/kunlun/base/kunlun-node-manager-1.0.1/bin && /bin/bash start_node_mgr.sh </dev/null >& start.log &
	
	cd /home/kunlun
	myReady=`echo "${selfIp}Ready"`
	bash ./send_ready.sh $metaIp $myReady
	#for i in `cat /home/kunlun/configure.txt | grep /self/hosts/meta_data_node-replica | grep /ip | awk '{print $2}'`; do python3 check.py --host $i --type kunlun; a=`echo $?`; while [[ "$a" != "0" ]]; do python3 check.py --host $i --type kunlun; a=`echo $?`; echo wait 1s...; sleep 1;  done; done
	for i in `cat /home/kunlun/configure.txt | grep /self/hosts | grep /ip | awk '{print $2}'`; do a=1; if [[ ! -f "${i}Ready" ]]; then a=1;echo $a; sleep 1; else a=0; fi; sleep 5; done

	# 发送api
	bash /home/kunlun/send_api.sh	

elif [[ "$selfRole" == "meta_data_node-replica" ]]
then
	metaseeds=`cat conf/metaSeed.txt`
        echo metaseeds = $metaseeds
        metaIpR=`cat conf/metaIp.txt`
        echo metaIpR = $metaIpR
        /bin/bash change_conf.sh meta "$metaseeds" "$metaIpR"

        # =======================================================================
        n=2
        for i in `cat configure.txt | grep /self/hosts/meta_data_node-replica/ | grep /ip | awk '{print $2}'`
        do
                echo $i
                if [[ "$i" != "$selfIp" ]]
                then
                        n=`echo "$n+1" | bc -l `
                elif [[ "$i" == "$selfIp" ]]
                then
                        serid=$n
                        echo yes!! $serid
                fi
        done
	clusterSeeds=`cat conf/clusterSeed.txt`
        echo `cat conf/clusterSeed.txt`
        clusterMetaSeeds=`cat conf/metaClusterSeed.txt`
        /bin/bash change_conf.sh cluster $selfIp "$clusterMetaSeeds" "$clusterSeeds"
	/bin/bash change_conf.sh node $selfIp "$clusterMetaSeeds"
        # =======================================================================
        tni=`echo "${serid}-1" | bc -l`
	#/home/kunlun/base/program_binaries/kunlun-server-1.0.1/scripts/meta_inuse.sql
	
	cd /home/kunlun
	a=1
        while [[ "$a" == "1" ]]; do if [[ ! -f "metaReady" ]]; then a=1;echo $a; sleep 1; else a=0; fi; sleep 5; done
	cd /home/kunlun/base/program_binaries/kunlun-storage-1.0.1/dba_tools
	python2 install-mysql.py --config=/home/kunlun/conf/mysql_meta.json --target_node_index=$tni --cluster_id=meta --shard_id=meta --server_id=$serid --ha_mode=mgr
	cd /home/kunlun/base/kunlun-cluster-manager-1.0.1/bin
        bash start_cluster_mgr.sh </dev/null >& start.log &
        #cd /home/kunlun/base/kunlun-node-manager-1.0.1/bin
        #bash start_node_mgr.sh </dev/null >& start.log &
	cd /home/kunlun
	myReady=`echo "${selfIp}metaRepReady"`
	bash ./send_ready.sh $metaIp $myReady

	cd /home/kunlun
	a=1
	while [[ "$a" == "1" ]]; do if [[ ! -f "ready" && ! -f 'noready' ]]; then a=1;echo $a; sleep 5; else a=0; fi; sleep 5; done
		
	sleep 5
	cd /home/kunlun/base/kunlun-cluster-manager-1.0.1/bin && /bin/bash restart_cluster_mgr.sh </dev/null >& start.log &
        cd /home/kunlun/base/kunlun-node-manager-1.0.1/bin && /bin/bash start_node_mgr.sh </dev/null >& start.log &
	cd /home/kunlun
	myReady=`echo "${selfIp}Ready"`
        bash ./send_ready.sh $metaIp $myReady

elif [[ "$selfRole" == "computing_node" ]]
then
	
	clusterMetaSeeds=`cat conf/metaClusterSeed.txt`
	/bin/bash change_conf.sh node $selfIp "$clusterMetaSeeds"
	#cd /home/kunlun/base/kunlun-node-manager-1.0.1/bin
        #bash start_node_mgr.sh </dev/null >& start.log &
	sleep 60
	cd /home/kunlun
	a=1
	while [[ "$a" == "1" ]]; do if [[ ! -f "ready" && ! -f 'noready' ]]; then a=1;echo $a; sleep 1; else a=0; fi; sleep 1; done	
	 
        cd /home/kunlun/
	bash copyPgLdd.sh
        bash start_node_mgr.sh $selfIp
	cd /home/kunlun
	myReady=`echo "${selfIp}Ready"`
        bash ./send_ready.sh $metaIp $myReady

elif [[ "$selfRole" == "data_node" ]]
then
	clusterMetaSeeds=`cat conf/metaClusterSeed.txt`
        /bin/bash change_conf.sh node $selfIp "$clusterMetaSeeds"
        #cd /home/kunlun/base/kunlun-node-manager-1.0.1/bin
        #bash start_node_mgr.sh </dev/null >& start.log &
	sleep 60
	a=1
	while [[ "$a" == "1" ]]; do if [[ ! -f "ready" && ! -f 'noready' ]]; then a=1;echo $a; sleep 1; else a=0; fi; sleep 1; done	

        cd /home/kunlun/
	bash start_node_mgr.sh $selfIp
	cd /home/kunlun
	myReady=`echo "${selfIp}Ready"`
        bash ./send_ready.sh $metaIp $myReady

elif [[ "$selfRole" == "data_node-replica" ]]
then	
	clusterMetaSeeds=`cat conf/metaClusterSeed.txt`
        /bin/bash change_conf.sh node $selfIp "$clusterMetaSeeds"
	sleep 60
	a=1
	while [[ "$a" == "1" ]]; do if [[ ! -f "ready" && ! -f 'noready' ]]; then a=1;echo $a; sleep 1; else a=0; fi; sleep 1; done	

        cd /home/kunlun/
	bash start_node_mgr.sh $selfIp
	cd /home/kunlun
	myReady=`echo "${selfIp}Ready"`
        bash ./send_ready.sh $metaIp $myReady

elif [[ "$selfRole" == "xpanel" ]]
then
	port=`cat /home/kunlun/configure.txt | grep /self/env/xpanel_port | awk '{print $2}'`
	cd /home/kunlun
	rm -rf /home/kunlun/base
	sudo service docker start
	sudo docker pull registry.cn-hangzhou.aliyuncs.com/kunlundb/kunlun-xpanel
	sudo docker run -itd --name xpanel1 -p $port:80 registry.cn-hangzhou.aliyuncs.com/kunlundb/kunlun-xpanel bash -c '/bin/bash /kunlun/start.sh'
fi
