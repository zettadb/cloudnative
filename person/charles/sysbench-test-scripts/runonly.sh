if [ $# -lt 7 ] ; then
       echo	
       echo get me 7 parameters,runing like	
	echo ./run.sh host port dbname user table_num table_size test_runtime       
	echo 'nohup /bin/bash `pwd`/runonly.sh 192.168.0.125 26252 postgres kunlun 10 10000000 120 > log.log 2>&1 &'
	echo
	exit 1
fi

for i in point_select delete insert read_only read_write write_only update_index update_non_index
do
        # create test result dir
        if [ ! -d $i ] ; then
                mkdir $i
        fi
done

#for i in 9
for i in 3 6 9 # run sysbench test 100 to 1000 threads
do
	li=` expr ${i} \* 100 `
	echo
	echo run threads ${li}
	echo
	./test.sh $1 $2 $3 $4 $li $5 $6 $7 
done

bash ./result.sh 
cp result result_before

for n in `seq 1 10`
do
        for a in point_select write_only insert update_index update_non_index
        do
                for i in 300 600 900
		do

                        b=`cat result | grep -A 11 "=== $a" | grep "|| $i ||" | awk '{print $16}' | sed 's/...$//'`
                        if [[ "$b" -eq '' ]]; then
                                echo
                                date
                                echo "rerun ${a}:${i}"
                                sysbench oltp_${a} --tables=$5 --table-size=$6 --db-ps-mode=disable --db-driver=pgsql --pgsql-host=$1 --report-interval=10 --pgsql-port=$2 --pgsql-user=$4 --pgsql-password=abc --pgsql-db=$3 --threads=${i} --time=$7 --rand-type=uniform run > ./${a}/${i}_${a} 2>&1
                        sleep 5
                        else
                                echo > /dev/null
                        fi
                done
        done
        bash ./result.sh
done

bash ./result.sh

#sysbench oltp_delete --tables=10 --table-size=100000 --db-driver=pgsql --pgsql-host=192.168.0.134 --pgsql-port=38701 --pgsql-user=abc --pgsql-db=postgres --pgsql-password=abc cleanup
