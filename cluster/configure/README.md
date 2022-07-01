* 该文件是用来配置集群参数的。
* 有两个文件，一个是configure.json，这个是用来指定配置的参数的。分了两个部分，一个是计算节点的配置，别一个是data和meta-data节点的共同配置。
  * 里面有几个默认的参数，是做个示范的。可以自己往上添加，只要符合json语法,参数名和值范围是正确的就行,后期如果有时间会考虑改成YAML格式，因为YAML语法更简洁且可以注释
  * 另一个是congfigure.py,可以通过`python3 configure.py --help` 来查看需要传递什么参数
  * 如果用的cluster_mgr或者xpenal安装的集群，要再多写一个install_xc.json(该文件为模版)的配置文件，然后`--install install_xc.json`
  * 如果是用的一键脚本直接把一键脚本的json配置文件就行，不用写install_xc.json
    * --defuser 集群的使用者
    * --defbase 集群的base目录
    * --install 集群的json配置文件,如 install.json
    * --config  集群配置的文件，如configure.json
    * --type    用的什么方式创建的集群，可以有'one_click','xpenal','cluster_mgr'
    * 示例：`python3 configure.py --defuser charles --defbase base-path --install install_xc.json --config configure.json --type cluster_mgr`
