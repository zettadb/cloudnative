if [[ $# -le 1 ]]
then
	echo start this scripts like : bash ./start.sh 192.168.0.113 5665
	exit 0
else
	echo
	echo -e "\033[32m install libmysql++-dev \033[0m"
	echo
	sudo apt-get install libmysql++-dev -y
	echo
	echo -e "\033[33m 编译中 \033[0m"
	echo -e "\033[31m gcc -I/usr/include/mysql -L/usr/lib/mysql mysql.c -lmysqlclient -o mysql \033[0m"
	gcc -I/usr/include/mysql -L/usr/lib/mysql mysql.c -lmysqlclient -o mysql
	echo 
	echo -e "\033[33m ./mysql ${1} ${2} \033[0m"
	./mysql ${1} ${2}
fi
