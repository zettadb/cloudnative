touch $2
echo "send $2 to $1"
expect -c "
    spawn scp /home/kunlun/$2 kunlun@$1:
    expect {
        \"yes/no\" {send \"yes\r\";exp_continue;}
        \"*password\" {set timeout 500;send \"pwd1\r\";}
    }
expect eof"
