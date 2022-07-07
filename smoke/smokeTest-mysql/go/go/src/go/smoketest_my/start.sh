Running this script requires two parameters
if [[ $# -le 1 ]]
then
	echo 'running this script requires two parameters, like : bash start.sh 192.168.0.113 5665'
	exit 0
fi

echo -e "\033[32m设置环境中... \033[0m"
go env -w GO111MODULE=on
go env -w GOPROXY=https://goproxy.cn,direct
go mod init smoketest_my
go mod tidy
go build
echo -e "\033[31m脚本测试中... \033[0m"
echo -e "\033[31m ./smoketest_my -h $1 -p $2 \033[0m"
./smoketest_my -h $1 -p $2

