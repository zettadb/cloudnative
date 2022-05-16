if [ $# -lt 7 ] ; then
       echo	
       echo get me 7 parameters,runing like	
	echo ./run.sh host port dbname user table_num table_size test_runtime       
	echo 'nohup /bin/bash `pwd`/prepare.sh 192.168.0.125 56556 postgres kunlun 10 100000 120 > log.log 2>&1 &'
	echo
	exit 1
fi



sysbench oltp_point_select        \
      --tables=$5                   \
      --table-size=$6           \
      --db-driver=pgsql             \
      --pgsql-host=$1        \
      --pgsql-port=$2             \
      --pgsql-user=$4         \
      --pgsql-password=abc \
      --pgsql-db=$3           \
      prepare


for i in point_select insert read_only read_write write_only update_index update_non_index
do
	# create test result dir
	if [ ! -d $i ] ; then
		mkdir $i 
	fi
done

#sysbench oltp_delete --tables=10 --table-size=100000 --db-driver=pgsql --pgsql-host=192.168.0.134 --pgsql-port=38701 --pgsql-user=abc --pgsql-db=postgres --pgsql-password=abc cleanup
