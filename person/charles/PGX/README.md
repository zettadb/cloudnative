* 该脚本有三个文件组成。
  * install.sh是用来配置通用配置参数的脚本，里面的配置项可以根据自己的情况来修改，默认的只是用来做示范的。
  * install.json 是集群的配置文件，可以根据自己的需求往上面添加或者减少节点。
  * pgx_install.py 就是脚本的主体。要传递的参数可以通过 `python3 pgx_install.py --help` 来查看
    * 示例：python3 pgx_install.py --type=pgxz --config=install.json --defbase=base-path --defuser=charles --package=tbase_bin_v2.0.tgz --opt=i
    * --type 有三个选项，分别是pgxc pgxl pgxz
    * --config 集群的配置文件, 默认install.json
    * --defbase 集群的base目录
    * --defuser 集群的默认linux用户
    * --package 集群的二进制包，要编译完成后的
    * --opt 有 `i` 和 `c`选项，i是install安装集群，c是clean清楚集群
