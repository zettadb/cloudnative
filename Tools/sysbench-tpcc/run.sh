
source ./par.sh
echo $1
#h=${2:-'192.168.0.113'}
#p=${3:-'5021'}
#u=${4:-'abc'}
#pwd=${5:-'abc'}
#d=${6:-'postgres'}
if [ "$1" = "" ];
then
	echo "please add parameter,run this scripts like './run.sh 1' or 'sh run.sh 1'"
	exit 0
else
	echo ====== run ========
	echo run $1 times
	echo host    = $host
	echo port    = $port
	echo user    = $user
	echo pwd     = $pwds
	echo bd      = $db
	echo times   = $time
	echo threads = $thread
	echo 
	echo ====== run ========
	echo

	#./tpcc.lua --pgsql-host=192.168.0.113 --pgsql-port=5021 --pgsql-user=abc --pgsql-password=abc --pgsql-db=postgres --use_fk=0 --threads=16 --tables=1 --scale=10 --trx_level=RC --db-ps-mode=auto --db-driver=pgsql prepare
	for i in `seq 1 $1`;
	do
		echo $i times
		./tpcc.lua --db-driver=pgsql --pgsql-host=$host --mysql-ignore-errors=1062 --pgsql-port=$port --pgsql-user=$user --pgsql-password=$pwds --pgsql-db=$db --time=$time --threads=$thread --report-interval=60 --tables=$table --scale=$wh --trx_level=RC --db-ps-mode=auto --rand-type=uniform  run
		
		sleep 5
	done
fi	
