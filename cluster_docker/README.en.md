# Copyright (c) 2019 ZettaDB inc. All rights reserved.
# This source code is licensed under Apache 2.0 License,
# combined with Common Clause Condition 1.0, as detailed in the NOTICE file.

This document describes how to install a kunlun database cluster with the docker images.  
With the images, each node of the cluster will be run inside a separate docker container.

* Files layout.
 There are the following files in this installation package:
 - kunlun-cluster-manager.tar.gz, kunlun-storage.tar.gz, kunlun-server.tar.gz : these are
     the files for docker images, they are used to create the containers. User
     should download these docker image files from downloads.zettadb.com, and put
     them into this directory. In downloads.zettadb.com, these files are located in the
     directory of $version/docker-multi , while $version means the product version.
 - install_docker.json: This is the sample configuration file for cluster. This file must
     be changed correctly before starting installation.
 - Other files are assistant installation scripts.
 Besides, the installation script will create some config files automatically.
  
For installation, we call the host where installing script is running on as the 'driver host', 
and call the hosts where the cluster nodes are running on as the 'cluster hosts'.

* Cluster Hosts Requirements
1 All cluster hosts should be Linux hosts, having sed and gzip installed and set in the PATH.
2 All cluster hosts should have docker installed. We test the installation on docker-ce 19, 
  so version 19 or upper is perferred. For installation, please refer to
    https://docs.docker.com/engine/install
3 All cluster hosts should have a user account with 'sudo without password' setting, 
  the user should also have a group name same with its user name. 
4 A network covering all the cluster hosts should be created with 'docker network create' command. 
  If there are multiple cluster hosts, all the cluster hosts should be set up properly with 
  'docker swarm init' or 'docker swarm join', and then the created network should be attachable, 
  like following:
	docker network create --driver overlay --attachable klnet
  For Redhat/CentOS, it requires some work to setup the docker swarm to work, please refer to:
    https://www.digitalocean.com/community/tutorials/how-to-configure-the-linux-firewall-for-docker-swarm-on-centos-7

* Driver Host Requirements
1 The script uses python2 to generate the commands, so python2 is needed. The script checks
  'python2' in PATH, and then 'python' if 'python2' is not found. If there is no 'python2' in PATH,
   make sure the command 'python' is version 2.
2 The driver host can access each cluster host with the user mentioned above via ssh without password.
  This means the cluster hosts should also have the dsa or rsa key verification set up.
3 The driver host needs to transfer the 3 image files(sum up to nearly 1GB) to all cluster hosts,
  so the network connection from driver host to each cluster host should not be too slow.

* Installation process
The command to install the cluster is like:
	bash install_docker.sh [defuser=user_to_be_used] [defbase=basedir_to_be_used]
the parameters of defuser=user_to_be_used and defbase=basedir_to_be_used are optional. 

This installation script uses a python script named 'generate_docker_scripts.py' and a
json file named 'install_docker.json' to generate the real commands and executes these
commands on cluster hosts.

The parameter of 'defuser=user_to_be_used' sets the default user name for the cluster hosts.
If a user is not specified for a cluster host, this name is used. If this option is not specified, 
the value is the current user name on the driver host.

The parameter of 'defbase=basedir_to_be_used' sets the directory to store the files, including the
docker image files and some generated configuration files. If the 'basedir' is not specified
for a cluster host, this directory will be used. If this option is not specified to installation script,
the value of '/kunlun' is used. The installation script will create the directory on the cluster hosts.

Examples:
1
	winter@wtz ~/kunlun-docker-0.8$ bash install_docker.sh defbase=.
The full real command is: bash install_docker.sh defbase=. defuser=winter
It uses winter(current user) as the user name to connect and operate the cluster hosts, unless we 
specify the a different user in 'install_docker.json'. It also stores all the files in the user's
home directory.

2
	winter@wtz ~/kunlun-docker-0.8$ bash install_docker.sh defbase=/scratch/kunlun defuser=kunlun
It uses kunlun as the default user name to connect and operate the cluster hosts, and uses /scratch/kunlun
as the default directory to store the all the related files. This style applies to the hosts where
the user's home directory is mounted from network and has a limit size for storage.

* The config file of 'install_docker.json'

The config file is used to specify the node configurations for the cluster. 
Generally, for a kunlun database cluster, there are the following components:
1 meta shard, consisting of some mysql nodes with group replication set.
2 some data shards(at least 1), each shard is consisting of some mysql nodes with group replication set.
3 computing nodes, each node is accepting client request and processing the request.
4 cluster manager node, used to manage the cluster. There is just one cluster manager node.

The top object in 'install_docker.json' contains 3 attributes:
1 network: specify the network for the containers to join, the default is 'klnet' if not specified.
  The network should be created by user before running the 'install_docker.sh'
2 machines: If a cluster host has different user name or base directory from the default values, 
  it is set here, just setting the non-default items here. If a host uses the default user and base
  directory, there is no need to specify here.
3 cluster: specify the nodes for the cluster, as mentioned above, there are 4 kinds of nodes.
  - for a node belonging to meta shard or data shards, two attribute needs to be set:
      * ip: specify the host ip where the docker container should be run on
	  * is_primary: specify whether this node is master in the shard. There should be one and only
	      one node with is_primary to be true in each shard.
	  * innodb_buffer_pool_size: this attribute is optional, it sets the buffer pool size for 
	      mysql's innodb storage engine. The value should be integer, and multiples of 1024.
	      If not specified, the value is 1073741824,which means 1G.
  - for a node belonging to computing nodes, the following attributes needs to be set:
	  * ip: specify the host ip where the docker container should be run on
	  * port: specify the port on the host to be used. this port be used to listen client requests.
	      If there are multiple computing nodes on same host, different ports should be set.
	  * user: The database user created for the computing node. It will have the access to 
	      the database of 'postgres'.
	  * password: The password for the database user. It should be ascii characters, and should
	      not contain the characters of single quote('), double quote(") and dollar($)
  - for cluster manager node, only one attribute needs to be set:
      * ip: specify the host ip where the docker container should be run on
	  
* Access the cluster
The cluster is accepting client data requests via the computing nodes. Each computing node is an
instance of postgres database server running inside a docker container.  So clients can connect
to the cluster using postgresql protocol, using the 'ip', 'port', 'user', 'password' configurations
in install_docker.json and the database name of 'postgres' as the connection parameters.

One example of using psql to access the cluster is like:
kunlun@kunlun-test:/kunlun$ psql -f /kunlun/test.sql postgres://kunlun:Tx1Df2Mn#@192.168.0.111:5401/postgres

Client can perform table and record-level operations, such as create/alter/drop tables, and DML operations.
The database operations, and cluster-level accounts management is still under development.
database of 'postgres' as the connecton string.
