if [[ $# -le 1 ]]
then
	echo run this script need 2 parameter ,like : bash ./start.sh 192.168.0.113 5665
	exit 0
fi
mkdir mysql
cd mysql
echo -e "\033[32m setting env... \033[0m"
echo -e "\033[32m dotnet new console \033[0m"
dotnet new console &
sleep 3
echo -e "\033[32mdotnet add package MySql.Data \033[0m"
dotnet add package MySql.Data
cp ../Program.cs .
cp ../start.sh .
echo
echo -e "\033[33m编译中\033[0m"
dotnet build
echo
echo -e "\033[31m开始测试... \033[0m"
loc=`find -name mysql | grep bin`
echo -e "\033[31m${loc} $1 $2 \033[0m"
${loc} $1 $2
