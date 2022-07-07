if [[ $# -le 1 ]]
then
	echo start this script like : bash ./start.sh 192.168.0.113 5665
	exit 0
else
	echo
	echo -e "\033[47;31m g++ mysql.cpp -lmysqlcppconn -o mysql \033[0m"
	echo
	g++ mysql.cpp -lmysqlcppconn -o mysql
	echo -e "\033[47;31m ./mysql \"tcp://${1}:${2}\" \033[0m"
	echo
	./mysql "tcp://${1}:${2}"
fi
