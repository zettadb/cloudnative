#./tpcc.lua --mysql-socket=/tmp/mysql.sock --mysql-user=root --mysql-db=sbt --time=300 --threads=64 --report-interval=1 --tables=10 --scale=100 --db-driver=mysql cleanup
sudo rm -rf ./par.sh
echo
echo ================ prepare ================
host=${1:-'192.168.0.105'} #default host
echo host = ${host}
echo host=${host} >> par.sh

port=${2:-'5401'} #default port
echo port = ${port}
echo port=${port} >> par.sh

db=${3:-'postgres'} #default dbname
echo dbname = ${db}
echo db=${db} >> par.sh

user=${4:-'abc'} #default user
echo user = ${user}
echo user=${user} >> par.sh

pwds=${5:-'abc'} #default pwd
echo pwd =  ${pwds}
echo pwds=${pwds} >> par.sh

table=${6:-'2'} #default table num
echo table num = ${table}
echo table=${table} >> par.sh

wh=${7:-'5'} #default warehouse num
echo warehouse num = ${wh}
echo wh=${wh} >> par.sh

thread=${8:-'30'} #default threads
echo threads = ${thread}
echo thread=${thread} >> par.sh

time=${9:-'15'} #default times
echo times = ${time}
echo time=${time} >> par.sh

echo ================ prepare ================
echo

echo ================ tips ===============
echo "run this like './prepare.sh host port dbname user pwd table_num scale_num threads_num times'"
echo "or vi ./prepare.sh to change parameter 'host port dbname user pwd table_num scale_num threads_num times'"
echo ================ tips ===============
echo

echo clean up database on 3s
sleep 3
echo

./tpcc.lua --pgsql-host=$host --pgsql-port=$port --pgsql-user=$user --pgsql-password=$pwds --pgsql-db=$db --use_fk=0 --threads=16 --tables=$table --scale=$wh --trx_level=RC --db-ps-mode=auto --db-driver=pgsql cleanup
echo 
echo prepare database on 3s
sleep 3
echo

./tpcc.lua --pgsql-host=$host --pgsql-port=$port --pgsql-user=$user --pgsql-password=$pwds --pgsql-db=$db --use_fk=0 --threads=16 --tables=$table --scale=$wh --trx_level=RC --db-ps-mode=auto --db-driver=pgsql prepare
