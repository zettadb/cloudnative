expect -c "
    spawn ssh $1 '$2'
    expect {
        \"yes/no\" {send \"yes\r\";exp_continue;}
        \"*password\" {set timeout 500;send \"pwd1\r\";}
    }
expect eof"

