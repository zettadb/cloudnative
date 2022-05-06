# Copyright (c) 2019 ZettaDB inc. All rights reserved.
# This source code is licensed under Apache 2.0 License,
# combined with Common Clause Condition 1.0, as detailed in the NOTICE file.

昆仑数据库集群一键工具使用说明

本说明描述了如何使用一键工具来进行集群的安装，启动，停止，以及清理动作。该工具运行于一台
Linux机器，根据指定的配置，把数据库集群的各个节点(存储节点群，计算节点群，集群管理节点）
安装到指定的目标机器上，并且搭建好集群。该工具还能停止集群，启动整个集群，以及清理整个集群。

基本要求:
1 所有节点所在机器须为Linux, 安装了bash, sed, gzip, python2等工具或者库。python 2可执行程序设置为python2
2 所有集群节点所在机器已经正确设置好用户，节点将以该用户启动，该用户能够运行sudo而不需要密码.
3 工具机器使用ssh通过默认端口登录节点所在机器，而不需要输入密码。具体做法可以搜索'ssh login without password'
4 对于安装存储节点的机器，需要预先安装以下库(此处为ubuntu 20.04): libncurses5 libaio-dev python-setuptools
5 对于安装计算节点的机器，需要预先安装以下库(此处为ubuntu 20.04): libncurses5 libicu66 python-setuptools gcc
6 对于安装动作，需要预先将二进制发布包 (以0.9.2为例，发布包为: kunlun-storage-0.9.2.tgz, kunlun-server-0.9.2.tgz,
   kunlun-cluster-manager-0.9.2.tgz ) 放入当前目录. 此外，工具运行机器和节点所在机器间网络不能太慢，因为需要将发布包传递到这些机器上。

文件布局:
当前目录下主要有以下文件:
 - 对于安装动作，需要有发布包(以0.9.2为例, 发布包为: kunlun-storage-0.9.2.tgz，kunlun-server-0.9.2.tgz，kunlun-cluster-manager-0.9.2.tgz),
   用户可以从downloads.zettadb.com下载这些发布包。对于已经发布的版本，这些包位于releases的对应版本下(0.8.4以后)或对应版本的release-binaries子目录下(0.8.3及以前); 
   而对于当前正在开发而未发布的版本，这些包位于: http://downloads.zettadb.com/dailybuilds/enterprise
 - 配置文件(比如install.json),
   主要用于配置节点的详细信息，包含节点所在机器，安装节点所用的用户名，以及节点特有的信息等。具体格式后面详细说明。
 - 其余为工具相关的文件，使用的基本流程是，先根据配置文件，产生实际运行的shell脚本，而后运行该脚本即可完成动作。

基本用法:
  python2 generate_scripts.py --action=install|stop|start|clean --config=config_file [--defuser=user_to_be_used] [--defbase=basedir_to_be_used]
  bash $action/commands.sh   # 其中$action=install|stop|start|clean

说明:
该工具集使用一个python脚本 'generate_scripts.py' 和一个json格式的配置文件来产生实际的安装命令序列(commands.sh),
而后运行这些命令序列即可以完成指定的动作。

* 参数 --action=动作，指定需要执行的动作，为install, stop, start, clean 四种之一

* 参数 --config=文件，指定配置文件。

* 参数 '--defuser=user_to_be_used'
设置集群的默认用户名。如果没有某机器配置，或该机器配置(machines，见后)中没有用户名的设置，则该默认用户名将被使用。
如果没有该选项，则默认用户名为运行脚本所在机器的当前用户名。

* 参数 '--defbase=basedir_to_be_used'
设置集群的默认工作目录。如果没有某机器设置，或者该机器设置(machines, 见后)中没有工作目录的设置，该默认工作目录将被使用。
该选项传入的目录必须为绝对路径。如果没有该选项，则'/kunlun'将作为默认的工作目录，
该目录将用于存放发布包，解压后的发布包，以及一些配置文件和辅助脚本文件等。

示例:

1 安装集群 install:
  # 使用install.json作为配置文件，使用klundb(非当前用户)作为集群默认用户名, /kunlun作为集群默认工作目录
  kunlun@kunlun-test2:~$python2 generate_scripts.py --action=install --config=install.json --defuser=klundb
  kunlun@kunlun-test2:~$bash install/commands.sh

2 停止集群 stop:
  # 使用install.json作为配置文件，/home/kunlun/programs作为集群默认工作目录，kunlun(当前用户)作为集群默认用户
  kunlun@kunlun-test2:~$python2 generate_scripts.py --action=stop --config=install.json --defbase=/home/kunlun/programs
  kunlun@kunlun-test2:~$bash stop/commands.sh

3 启动集群 start:
  # 使用install.json作为配置文件，/kunlun作为集群默认工作目录，kunlun(当前用户)作为集群默认用户
  kunlun@kunlun-test2:~$python2 generate_scripts.py --action=start --config=install.json
  kunlun@kunlun-test2:~$bash start/commands.sh

4 清理集群(停止集群，并删除所有安装的节点及数据) clean:
  # 使用install.json作为配置文件，/kunlun作为集群默认工作目录，wtz(当前用户)作为集群默认用户
  wtz@kunlun-test2:~$python2 generate_scripts.py --action=clean --config=install.json
  wtz@kunlun-test2:~$bash clean/commands.sh

配置文件说明:

对于不同的动作，可以允许配置文件的内容有所不同，但一般都使用install动作的配置文件。由于目录结构的因素，
要求start/stop/clean操作的集群，也是使用该工具的install动作操作产生的。

配置文件分为两大部分，可选的machines部分，和cluster部分。
* machines用来设置节点所在机器的信息，主要用来设置机器上的默认工作目录, 使用的默认用户名。每个machine条目配置说明如下:
  {
    "ip":"192.168.0.110",   # 机器的IP
    "basedir":"/kunlun",  # 该机器的默认工作目录
    "user":"kunlun"  # 在该机器执行动作的默认用户名
  }
* cluster则用来设置集群的信息。集群信息分为五部分
  - name: 集群名字，一般使用字母和数字的组合
  - meta: 元数据集群的信息
  - comp: 计算节点集的信息
  - data: 数据节点集的信息
  - clustermgr: 集群管理节点的信息(只需要一个)
* 元数据集群为一个存储节点复制组，一主多备，内部含有2个或2个以上(一般建议>=3的奇数)的存储节点。
* 数据节点集为多个存储节点复制组，一个复制组即为一个数据分片。每个复制组内部含有2个或2个以上(一般建议>=3的奇数)存储节点。
* 计算节点集为一到多个计算节点，是客户端的接入点。具体数取决于需要的接入点数目。

对于每个存储节点，基于mysql-8.0.26开发， 一般需要以下信息:
   {
     "is_primary":true,  # 是否为复制组中的初始主节点，一个复制组有且仅有一个主节点，仅install需要
     "ip":"192.168.0.110", # 节点所在机器的ip
     "port":6001, # mysql port
     "xport":60010, # mysql xport，仅install需要
     "mgr_port":60011, # 用于mysql group replication通信的节点，仅install需要
     "innodb_buffer_pool_size":"64MB", # innodb的buffer pool大小，测试环境可以小一点，生产环境一般需要大一些。仅install需要
     "data_dir_path":"/data1", # mysql数据目录，仅install需要
     "log_dir_path":"/data1/log", # mysql binlog，服务器日志等的存放位置，仅install需要
     "innodb_log_dir_path": "/data2/innodblog", # mysql innodb log存放位置，可以没有，如果没有设置，
                                                # 则默认在log_dir_path指定的目录下，仅install用到
     "user":"kunlun", # 运行mysql服务器进程的用户，一般应当与machines里面的对应条目使用相同的值，仅install需要
     "election_weight":50 mysql group replication的选举权重。一般50即可，仅install需要
  }

对于每个计算节点，基于postgresql-11.5开发，一般需要以下信息:
    {
       "id":1,   # 数字标识，每个节点需不用，一般从1开始，仅install需要。
       "name":"comp1",  # 名称, 每个节点需不同，参照例子即可，仅install需要。
       "ip":"192.168.0.110", # 节点所在机器的IP，用于客户端连接
       "port":5401, # 端口，用于客户端连接
       "user":"abc", # 用户名，用于客户端连接，仅install需要。
       "password":"abc", # 密码，用于客户端连接，仅install需要。
       "datadir":"/pgdatadir" # 节点的安装目录，用于存放节点数据。仅install需要。
    }

对于集群管理节点，只需要一个信息:
* ip: 节点所在机器的IP

具体配置可以参照示例:install.json.

集群安装或启动后，可以通过计算节点访问集群，进行各种支持的数据操作。计算节点都基于PostgreSQL-11.5开发，
所以可以通过postgresql协议来连接计算节点，发出各种操作请求。本工具提供了一个简单的测试，来验证
集群连接和进行冒烟测试, 调用方式如下:

kunlun@kunlun-test:cluster$ psql -f smokeTest.sql postgres://user:password@ip:port/postgres

其中用户名，密码，ip，端口需要改为对应的计算节点设置的内容。

smokeTest.sql的下载地址为: https://gitee.com/zettadb/cloudnative/blob/main/smoke/smokeTest.sql
