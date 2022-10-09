## mysql协议smoketest脚本编译及运行
* 以下脚本仅在ubuntu测试过
### c
* `cd c`
* `./start.sh 192.168.0.126 8883`

### c#
* `cd c#`
* `./start.sh 192.168.0.126 8883`

### cpp
* `cd cpp`
* `./start.sh 192.168.0.126 8883`

### go
* `cd go/go/src/go/smoketest_my`
* `/bin/bash start.sh 192.168.0.126 8883`

### java
* `cd  java`
* `./start.sh 192.168.0.126 8883`

### js
* `cd js`
* `sudo apt install npm`
* `npm install mysql`
* `node smoketest-my.js 192.168.0.126 8883`

### python
* `cd python`
  * 该文件下有三个文件，smokeTest-my.py用的pymysql的库
  * smokeTest.py 是用的psycopg2的包
  * mysql-connector-test.py 用的是 mysql-connector/python
  * `pip install psycopg2`
  * `pip3 install pymysql`
  * `pip3 install mysql-connector-python`
* 运行
  * `python3 smokeTest-my.py 192.168.0.126 8883`
  * `python2 smokeTest.py 192.168.0.126 8883`
  * `python3 mysql-connector-test.py --host 192.168.0.126 --port 8883`

### php
* `php smoketest-my.php host port`

### sql
* `mysql -h 192.168.0.126 -pabc -uabc -P8883 -D mysql < smokeTest-my.sql`

### rust
* `cd rust`
* `bash start.sh 192.168.0.126 8883`
