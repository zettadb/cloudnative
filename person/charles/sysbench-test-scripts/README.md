这个脚本是我用来做sysbench竞品对比的。 
* 用法直接`./run.sh` 或者 `./runonly.sh`就可以看到  
run.sh 是对集群做灌数据加测试加检查加出结果,最后清除数据的。  
runonly.sh 是只测试，加出结果的  
result.sh 是用来出结果的  
prepare.sh 是用来准备数据的  
test.sh 是测试一次的脚本  
plus_result.sh 是用来处理多个sysbench结果的脚本，因为后面不用haproxy，所以要起多个sysbench  
  * plus_result.sh使用方法
```
1.先创建**计算节点个数**的文件夹。该文件夹命名不限制，假设有三个计算节点且以下用comp1 comp2 comp3代替

2.每一个文件夹里面都要放run.sh runonly.sh result.sh prepare.sh test.sh

3.新建一个启动脚本，使用&后台运行确保起动三个节点，内容如：
cd comp1 && nohup /bin/bash `pwd`/runonly.sh 192.168.0.132 8888 postgres abc 10 10000000 300 > log.log 2>&1 &
cd comp2 && nohup /bin/bash `pwd`/runonly.sh 192.168.0.134 8888 postgres abc 10 10000000 300 > log.log 2>&1 &
cd comp3 && nohup /bin/bash `pwd`/runonly.sh 192.168.0.140 8888 postgres abc 10 10000000 300 > log.log 2>&1 &

4.运行启动脚本并运行完毕后，在于comp1，comp2.comp3文件夹同级目录下使用plus_result.sh:
bash ./plus_result.sh comp1 comp2 comp3
  注意传递的文件名不可以加 / 号
5.查看同级目录下allresult.txt结果会输出在 allresult.txt里面
allresult.txt 线程数和tps、qps是三个计算节点相加的结果
avg是所有计算节点结果相加再除计算节点个数
.95是拿所有计算节点最大的结果

```

* run.sh和runonly.sh 都是会在所有的sysbench测试走完一遍后检查，
  * 如果其中的一个指标的某个线程的结果是空的，那就直接运行该指标该线程的sysbench测试
  * 检查设置了100次，100次后如果还是有空的，那直接当有问题处理了
* 出结果和准备数据与测试单次的脚本都是可以独自运行的
* 默认是kunlun集群，如果有其它的集群，可以`sed -i 's/kunlun/kunlun/g' result.sh` 改变脚本的输出
