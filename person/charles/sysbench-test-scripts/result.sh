rm -rf result
touch result

for list in point_select insert read_only read_write write_only update_index update_non_index
do
        echo "== ${list} == " >> result
        #for a in `seq 1 10`
	for a in 3 6 9
        do
                la=`expr $a \* 100`
                wcl=`cat ${list}/${la}_${list} | grep tps | wc -l`
                tps=`cat ${list}/${la}_${list} | awk '{print $7}' | awk '{sum+=$1}END{printf "%.2f", sum}'`
                tpa=`echo "scale=2;${tps}/${wcl}" | bc -l`
                rea=`cat ${list}/${la}_${list} | grep read: | awk '{print $2}'`
                wri=`cat ${list}/${la}_${list} | grep write: | awk '{print $2}'`
                txn=`cat ${list}/${la}_${list} | grep transactions: |  awk '{print $2}'`
                avg=`cat ${list}/${la}_${list} | grep avg: |  awk '{print $2}'`
                thp=`cat ${list}/${la}_${list} | grep 95th |  awk '{print $3}'`
                toe=`cat ${list}/${la}_${list} | grep 'events (avg/stddev):' | awk '{print $3}'`
                echo $la $tpa $rea $wri $txn $avg $thp $toe >> result
        done
        echo >> result
done

sed -i 's/ / || /g' result && sed -i 's/^/|| kunlun || /' result
sed -i 's/$/ ||/' result
sed -i "1 i * `date`" result && sed -i "1 i [[PageOutline]]" result

for i in point_select insert read_only read_write write_only update_index update_non_index
do
	ai=`cat -n result | grep $i | awk '{print $1}'`
	sed -i "$ai a\|| db || threads || tps(avg) || read || wirte || txn || avg response time(ms) || .95 response time(ms) || total events ||" result
done

sed -i 's/|| kunlun ||  ||/----/' result && sed -i 's/|| kunlun || == || /=== /' result
sed -i 's/ || == ||  ||//' result && cat result
