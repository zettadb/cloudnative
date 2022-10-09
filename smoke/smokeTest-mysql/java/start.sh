if [[ $# -le 1 ]]
then
	echo start this scripts like "./start.sh 192.168.0.113 5665"
	exit 0
fi

if [[ -e ./mysql-connector-java-8.0.16.jar ]]
then
	echo
	echo -e `pwd` already has "\033[32m mysql-connector-java-8.0.16.jar \033[0m", now "\033[33m start \033[0m" jdbc-mysql smoke test
	echo
else
	echo
	echo -e can not found "\033[32m mysql-connector-java-8.0.16.jar \033[0m", now "\033[33m downloading \033[0m"...
	echo
	wget https://static.runoob.com/download/mysql-connector-java-8.0.16.jar
fi

echo -e "\033[47;31;5m java -cp mysql-connector-java-8.0.16.jar mysql.java ${1}:${2} \033[0m"
echo
javac mysql.java
java -cp .:mysql-connector-java-8.0.16.jar mysql ${1}:${2}
