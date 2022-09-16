## 各smoke test脚本编译及运行方式
* mysql 协议的smoke test脚本在smokeTest-mysql目录里面, 当前目录都是pg协议的
### python
* 要安装psycopg2
  * `pip install psycopg2`
* `python2 smokeTest.py $host $port`
* 例如：`python2 smokeTest.py 192.168.0.126 8881`
### java
* 要下载pg官方的connector，可以使用本目录的postgresql-42.2.16.jar,以下例子以该jar包为例
* 编译：
  * `javac smokeTest.java`
* 运行 `java -cp .:./postgresql-42.2.16.jar smokeTesta host port`
  * 如：`java -cp .:./postgresql-42.2.16.jar smokeTesta 192.168.0.126 8881`
* 如果有说package 相关的错误，把第一行的package删了重新编译就行
### go
* 环境：如果是还没用过pg相关包，需要做这一步
```
   cd `pwd`/go/go/src/go/smoketest
   go env -w GO111MODULE=on
   go env -w GOPROXY=https://goproxy.cn,direct
   go mod init smoketest_my #初始化脚本
   go mod tidy #该步go的包管理器会把依赖库自动处理好
   go build # build
```
* 运行：`./smoketest.go -h host -p port`
  * 如： `./smoketest.go -h 192.168.0.126 -p 8881`

### sql
* `psql -f smokeTest.sql postgres://user:pwd@host:port/dbname`

### js
* 在安装完npm工具和nodejs后，使用`npm install pg`下载connector
* `cd js`
* 运行：`node smokeTest.js host port`
  * 如：`node smokeTest.js 192.168.0.126 8881`

### c#
* 在安装完dotnet和dotnet_runtime后，`cd smoketest.c#`
* 环境：要新建一个目录，smoketest.c#的bin目录和obj目录里的文件都是很老的
  * `mkdir test && dotnet new console && cp ../Program.cs .`
* 编译：`dotnet build`
* 使用find命令找到产生的二进制文件: 
```
app=`find -name test | grep bin`
```
* 运行：`$app host port`
  * 如：`$app 192.168.0.126 8881`

### c++
* 环境：
 * `sudo apt install libpq-dev`
 * `git clone https://github.com/jtv/libpqxx.git`
 * `cd libpqxx`
 * `./configure`
 * `make`
 * `sudo make install`
* 编译
 * `g++ -o smokeTest smokeTest.cpp -lpqxx -lpq -std=c++17`
* 运行 
  * `./smokeTest "dbname = postgres host=127.0.0.1 port=5401 user=abc password=abc"`

### c
* 编译
  * ` * gcc -o smokeTest smokeTest.c -I/path/postgresql-11.5-rel/include -L/path/postgresql-11.5-rel/lib -lpq`

* 运行
  * `./smokeTest "dbname = postgres host=127.0.0.1 port=5401 user=abc password=abc"`

### php
* 运行
  * `php smokeTest 192.168.0.126 8881`

### rust
* 编译：
  * `cd rust`
  * `cargo build`
* 运行:
```
app=`find -name rust_postgres`
$app -h 192.168.0.126 -p 8881
```
