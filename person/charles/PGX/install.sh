types=$1
host=$2
port=$3
nodename=$4
path=$5
user=$6
pooler_port=$7
mhost=$8
mport=$9
mname=${10}
muser=${11}

if [[ "$types" ==  'gtm' ]]
then
	cat > $path/gtm.conf << EOF
nodename = $nodename
listen_addresses = '*'
port = $port
startup = ACT
EOF

elif [[ "$types" == 'gtm_slave' ]]
then
       cat >> $path/gtm.conf << EOF
nodename = $nodename
listen_addresses = '*'
port = $port
startup = STANDBY
active_host = '$host'
active_port = $user
EOF

elif [[ "$types" ==  'cn' ]]
then
        cat >> $nodename/postgresql.conf << EOF
port =$host
pooler_port=$port
include_if_exists ='/home/kunlun/TPC/postgres-xz/global/postgresql.conf.user'
wal_level = replica
wal_keep_segments =256
max_wal_senders =4
archive_mode = on
archive_timeout =1800
archive_command ='echo 0'
log_truncate_on_rotation = on
log_filename ='postgresql-%M.log'
log_rotation_age =4h
log_rotation_size =100MB
hot_standby = on
wal_sender_timeout =30min
wal_receiver_timeout =30min
shared_buffers =1024MB
max_pool_size =2000
log_statement ='ddl'
log_destination ='csvlog'
logging_collector = on
log_directory ='pg_log'
listen_addresses ='*'
max_connections =2000
gtm_host = '$path'
gtm_port = $user
EOF

	cat >> $nodename/pg_hba.conf << EOF
host    replication     all             0.0.0.0/0               trust
host    all             all             0.0.0.0/0               trust
EOF

elif [[ "$types" ==  'dn' ]]
then
        cat >> $nodename/postgresql.conf << EOF
port =$host
pooler_port=$port
include_if_exists ='/data/tbase/global/postgresql.conf.user'
listen_addresses ='*'
wal_level = replica
wal_keep_segments =256
max_wal_senders =4
archive_mode = on
archive_timeout =1800
archive_command ='echo 0'
log_directory ='pg_log'
logging_collector = on
log_truncate_on_rotation = on
log_filename ='postgresql-%M.log'
log_rotation_age =4h
log_rotation_size =100MB
hot_standby = on
wal_sender_timeout =30min
wal_receiver_timeout =30min
shared_buffers =1024MB
max_connections =4000
max_pool_size =4000
log_statement ='ddl'
log_destination ='csvlog'
wal_buffers =1GB
gtm_host = '$path'
gtm_port = $user
EOF
        cat >> $nodename/pg_hba.conf << EOF
host    replication     all             0.0.0.0/0               trust
host    all             all             0.0.0.0/0               trust
EOF

elif [[ "$types" ==  'dn_slave' ]]
then
        cat >> $nodename/postgresql.conf << EOF
port =$host
pooler_port=$port
EOF
        cat >> $nodename/pg_hba.conf << EOF
host    replication     all             0.0.0.0/0               trust
host    all             all             0.0.0.0/0               trust
EOF
	cat >> $nodename/recovery.conf << EOF
standby_mode = on
primary_conninfo ='host = $path port = $user user = $pooler_port application_name = $mhost'
EOF

fi

if [[ "$types" == "cn" && "$pooler_port" == "pgxc" ]]
then
	sed -i 's/wal_level = replica/wal_level = archive/' $nodename/postgresql.conf
elif [[ "$types" == "dn" && "$pooler_port" == "pgxc" ]]
then
	sed -i 's/wal_level = replica/wal_level = hot_standby/' $nodename/postgresql.conf
fi
