========================================================================================================

install sysbench before run tpcc:

sudo apt-get install sysbench

-prepare data :

./prepare.sh host port dbname user pwd table_num scale_num threads_num times

or vi ./prepare.sh to change defult parameter values 'host port dbname user pwd table_num scale_num threads_num times'

-run :

./run.sh 

You can modify the run parameters in par.sh after preparation

before do ./run.sh, you need to install the -socket environment:

	wget http://www.lua.org/ftp/lua-5.1.5.tar.gz

	tar-xf lua-5.1.5.tar.gz

	cd lua-5.1.5

	make linux

	make install

        cd luasocket-2.0.2/

        make

        sudo make install

=============================================================================================================

在运行之前要先安装sysbench，apt-get install sysbench 或者 yum install sysbench就行了

相较于标准的sysbench-tpcc，删除了tpcc_common.lua文件里的FOR UPDATE操作，增加了PARTITION 分区分表功能。

增加了prepare.sh和run.sh文件，方便prepare data和运行 sysbench-tpcc。

因为本人对lua不是很熟悉，所以运行多次后就会出现 duplicate 的问题，所以运行一段时间后要重新prepare一次

prepare:

运行prepare.sh文件时要提供以下参数:(以下参数皆有默认值,不用所有参数都改)

        host port dbname user pwd table_num scale_num threads_num times

        主机 端口 数据库 用户 密码 表数量   scale数量  线程数     运行时间s

        ./prepare.sh host port dbname user pwd table_num scale_num threads_num times
	
	如: ./prepare.sh 192.168.0.1 5432 postgres root root 10 100 300 30
	
	table_num和scale_num越大，灌的数据量越多

可以直接在prepare.sh文件里面改对应的默认参数，改完后直接运行 ./prepare.sh

运行完后会在当前目录生成一个 par.sh 文件，该文件是存放运行sysbench-tpcc要提供的参数

这些参数就是在 prepare.sh 提供的参数，如果要改可以直接在par.sh文件里面改

run:

prepare完后，运行sysbench-tpcc,直接运行run.sh

run.sh会直接获取par.sh里面的参数，如果要改sysbench-tpcc的运行参数直接在par.sh里面改就行。

环境：

在run之前，要确保有luasocket环境

如果没有环境，请按以下步骤进行(luasocket在lua5.2以后就不支持了，所以选用5.1.5)

(以下仅供参考，如果以下步骤报错去google自行解决)

	wget http://www.lua.org/ftp/lua-5.1.5.tar.gz

	tar-xf lua-5.1.5.tar.gz

	cd lua-5.1.5

	make linux

	make install

        cd luasocket-2.0.2/

        make

        sudo make install

安装完后，尝试socket是否安装成功！

在当前目录输入

        lua

进入lua界面，输入

        require('socket')

如果没有报错，恭喜你安装成功！

=============================================================================================================

