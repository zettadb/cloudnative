rm -rf allresult.txt
touch allresult.txt
echo $#
for sn in point_select point_select_k insert write_only read_only read_only_k read_write read_write_k update_index update_non_index
do
	echo "== $sn" >> allresult.txt
	echo '|| db || threads || tps || pqs || avg response time(ms) || .95 response time(ms) ||' >> allresult.txt

	for tn in `seq 1 3`
	do
		for i in $*
		do
			num=`echo "scale=0;3+2" | bc -l`
			export thd$i=`cat $i/result | grep -A $num "$sn" | grep -v "$sn" | grep -v threads | sed -n "${tn}p" | awk '{print $4}'`
			export tps$i=`cat $i/result | grep -A $num "$sn" | grep -v "$sn" | grep -v threads | sed -n "${tn}p" | awk '{print $6}'`
			export qps$i=`cat $i/result | grep -A $num "$sn" | grep -v "$sn" | grep -v threads | sed -n "${tn}p" | awk '{print $8}'`
			export avg$i=`cat $i/result | grep -A $num "$sn" | grep -v "$sn" | grep -v threads | sed -n "${tn}p" | awk '{print $10}'`
			export p95$i=`cat $i/result | grep -A $num "$sn" | grep -v "$sn" | grep -v threads | sed -n "${tn}p" | awk '{print $12}'`
		done
		sumthd=`env | grep ^thd | awk -F= '{print $2}' | awk '{sum+=$1}END{print sum}'`
		sumtps=`env | grep ^tps | awk -F= '{print $2}' | awk '{sum+=$1}END{print sum}'`
		sumqps=`env | grep ^qps | awk -F= '{print $2}' | awk '{sum+=$1}END{print sum}'`
		sumavg=`env | grep ^avg | awk -F= '{print $2}' | awk '{sum+=$1}END{print sum}'`
		sump95=`env | grep ^p95 | awk -F= '{print $2}' | awk '{sum+=$1}END{print sum}'`
		avgavg=`echo "scale=2;$sumavg/$#" | bc -l`
		maxp95=`env | grep ^p95 | awk -F= '{print $2}' | sort | sed -n '$p'`
		echo "|| kunlun || $sumthd || $sumtps || $sumqps || $avgavg || $maxp95 ||" >> allresult.txt
	done
	echo '----' >> allresult.txt
done
