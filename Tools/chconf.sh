#statement_timeout = 30000 
#lock_timeout = 20000
#log_min_duration_statement = 300
#mysql_read_timeout = 30
#mysql_write_timeout = 30


echo postgres
ps -ef | grep postgre | grep charles | grep bin | awk '{print $10}' >> my_post.txt
pos=`cat my_post.txt | wc -l`


for i in `seq 1 $pos`
do
	echo $i
	nu_pos=$(awk "NR==${i}{print}" my_post.txt)
	echo "=========change ${nu_pos}/postgresql.conf success!========"
	echo
	sed -i 's/statement_timeout = 30000/statement_timeout = 3000000/'               ${nu_pos}/postgresql.conf
	sed -i 's/lock_timeout = 20000/lock_timeout = 2000000/'                         ${nu_pos}/postgresql.conf
	sed -i 's/log_min_duration_statement = 300/log_min_duration_statement = 30000/' ${nu_pos}/postgresql.conf
	sed -i 's/mysql_read_timeout = 30/mysql_read_timeout = 3000/'                   ${nu_pos}/postgresql.conf
	sed -i 's/mysql_write_timeout = 30/mysql_write_timeout = 3000/'                 ${nu_pos}/postgresql.conf

done
#=====================================================================================================================


#innodb_lock_wait_timeout = 20
#lock_wait_timeout   =   5
echo mysql
ps -ef | grep mysql | grep charles | grep user= | awk '{print $10}'  >> my_sql.txt
sed -i 's?--defaults-file=/?/?' my_sql.txt
mys=`cat my_sql.txt | wc -l`

for i in `seq 1 ${mys}`
do
	echo $i
	nu_mys=$(sed -n "${i}p" my_sql.txt)
	echo "========change ${nu_mys} success!========"
	echo 
	sed -i 's/innodb_lock_wait_timeout = 20/innodb_lock_wait_timeout = 200/' ${nu_mys}
	sed -i 's/lock_wait_timeout   =   5/lock_wait_timeout   =   100/'        ${nu_mys}
done



rm my_post.txt my_sql.txt
