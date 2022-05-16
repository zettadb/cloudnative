这个脚本是我用来做sysbench竞品对比的。 
* 用法直接`./run.sh` 或者 `./runonly.sh`就可以看到  
run.sh 是对集群做灌数据加测试加检查加出结果,最后清除数据的。  
runonly.sh 是只测试，加出结果的  
result.sh 是用来出结果的  
prepare.sh 是用来准备数据的  
test.sh 是测试一次的脚本  
* run.sh和runonly.sh 都是会在所有的sysbench测试走完一遍后检查，
  * 如果其中的一个指标的某个线程的结果是空的，那就直接运行该指标该线程的sysbench测试
  * 检查设置了100次，100次后如果还是有空的，那直接当有问题处理了
* 出结果和准备数据与测试单次的脚本都是可以独自运行的
* 默认是kunlun集群，如果有其它的集群，可以`sed -i 's/kunlun/kunlun/g' result.sh` 改变脚本的输出
