* 该脚本是用来发送cluster_mgr的接口请求的
== 详细说明
* 有两个文件：
  * 一个是config.yaml
    * 该文件是配置文件，按照yaml格式的要求填就行
  * 然后就是脚本
    * --type , `install` 或者 `delete`,就是安装集群或者是删除集群，默认`install`
    * --config, 就是配置文件，默认是`config.yaml`
