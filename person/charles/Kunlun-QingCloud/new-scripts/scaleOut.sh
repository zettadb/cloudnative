cd /home/kunlun/
nets=`cat /etc/confd/confd.toml  | grep nodes | awk -F= '{print $2}' | sed 's/^...//' | sed 's/..$//'`
curl $nets > /home/kunlun/scaleOut.txt
selfRole=`cat /home/kunlun/scaleOut.txt | grep /self/host/role | awk '{print $2}'`
metaIp=`cat /home/kunlun/scaleOut.txt | grep /self/hosts/meta_data_node/ | grep /ip | awk '{print $2}'`
selfIp=`cat scaleOut.txt | grep self/host/ip | awk '{print $2}'`
#scaleIp1=`diff configure.txt scaleOut.txt | grep self/hosts/data_node/ | grep /ip | head -1 | awk '{print $3}'`

if [[ "$selfRole" = "meta_data_node" ]]
then	
	#更新配置
	diff /home/kunlun/configure.txt /home/kunlun/scaleOut.txt > diff.txt
	#把旧的群集信息发送给所有要扩容的服务器
	for i in `cat /home/kunlun/diff.txt | grep /self/hosts | grep /ip | awk '{print $3}'`
	do
		/bin/bash /home/kunlun/send_ready.sh $i /home/kunlun/configure.txt
		/bin/bash /home/kunlun/send_ready.sh $i ready
	done

elif [[ "$selfRole" = "data_node" ]]
then
	#配置配置信息，找出新增的第一个主节点
	diff /home/kunlun/configure.txt /home/kunlun/scaleOut.txt > diff.txt
	scaleIp1=`diff configure.txt scaleOut.txt | grep self/hosts/data_node/ | grep /ip | head -1 | awk '{print $3}'`

	if [[ "$selfIp" == "$scaleIp1" ]]
	then
		#当节点是主节点且为第一个时，让meta节点运行scaleOut.sh脚本
		/bin/bash /home/kunlun/remote_run.sh $metaIp /home/kunlun/scaleOut.sh
		#检测meta节点是否发送完成diff /home/kunlun/configure.txt /home/kunlun/scaleOut.txt > diff.txt
		#while [[ "$a" == "1" ]]; do if [[ ! -f "ready" ]]; then a=1;echo $a; sleep 1; else a=0; fi; sleep 5; done
	fi
	a=1;while [[ "$a" == "1" ]]; do if [[ ! -f "ready" ]]; then a=1;echo $a; sleep 1; else a=0; fi; sleep 5; done
fi
