if [[ $# -le 1 ]]
then
        echo run this script need 2 parameter ,like : bash ./start.sh 192.168.0.113 5665
        exit 0
fi
pwds=`pwd`
echo -e "\033[32mcurrent path : $pwds \033[0m"
echo
sed -i "s/192.168.0.113/$1/g" src/main.rs
sed -i "s/5662/$2/g" src/main.rs
cd src
echo -e "\033[31m编译中... \033[0m"
echo
cargo build
cd $pwds
sc=`find -name rust-mysql`
echo -e "\033[33m运行脚本... \033[0m"
$sc

sed -i "s/$1/192.168.0.113/g" src/main.rs
sed -i "s/$2/5662/g" src/main.rs
