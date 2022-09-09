cd /home/kunlun
rm -rf conf/tableList.txt
metaIp=`cat configure.txt | grep /self/hosts/meta_data_node/ | grep /ip | awk '{print $2}'`
echo "select DISTINCT(shard_id) from shard_nodes;" > tmp/a.txt
mysql -h $metaIp -P6001 -ppwd3 -upgx kunlun_metadata_db < tmp/a.txt | sed '1d' > conf/shards.txt
echo "select hostaddr from cluster_mgr_nodes where member_state = 'source'" > tmp/a.txt
clusterMgrPrimary=`mysql -h $metaIp -P6001 -ppwd3 -upgx kunlun_metadata_db < tmp/a.txt | tail -1`

for i in `cat conf/shards.txt`
do
	paras=\"version\":\"1.0\",\"job_id\":\"\",\"job_type\":\"get_expand_table_list\",\"timestamp\":\"1435749309\",\"user_name\":\"kunlun\",\"paras\":{\"cluster_id\":\"1\",\"shard_id\":\"$i\",\"policy\":\"top_size\"}
	curl -d "{$paras}" -X POST http://$clusterMgrPrimary:56000/HttpService/Emit > tmp/a.txt
	cat tmp/a.txt | awk -F: '{print $3}' | awk -F} '{print $1}' | sed 's/"//g' | sed 's/,/ /' > tmp/b.txt
	for b in `cat tmp/b.txt`
	do
		echo $b $i >> tmp/c.txt
	done
done

cat tmp/c.txt | awk -F. '{print $2,$3}' | sed 's/_$$_/./' | sed 's/ /./' > conf/tableList.txt

if [[ -f "/home/kunlun/conf/old_tableList.txt" ]]
then	
	rm -rf /home/kunlun/conf/first_scaleOut
	diff /home/kunlun/conf/old_tableList.txt /home/kunlun/conf/tableList.txt > /home/kunlun/conf/tmp_tableList.txt
	sed -i 's/^..//' /home/kunlun/conf/tmp_tableList.txt
	for i in `cat /home/kunlun/conf/tmp_tableList`
	do
		echo $i >> /home/kunlun/conf/old_tableList.txt
	done

	mv /home/kunlun/conf/tmp_tableList.txt /home/kunlun/conf/tableList.txt
else
	cp -rf /home/kunlun/conf/tableList.txt /home/kunlun/conf/old_tableList.txt
	touch /home/kunlun/conf/first_scaleOut
fi



#a=`sed 's/^/"/' a.txt | sed 's/ /":"/' | sed 's/$/",/'`
