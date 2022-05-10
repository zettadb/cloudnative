* 该脚本是用来监控cpu、io等服务器状态的,
* 每10s查询一次，然后写入到文件里面
* 然后每1个小时删除一次binlog，防止日志太多占满空间，计算节点自动退出
* `python3 clean-check.py --help` 查看其要传递的参数
  * --config 群集的json配置文件
  * --defuser 集群的默认用户
  * 示例：python3 clean-check.py --config=install.json --defuser=kunlun
