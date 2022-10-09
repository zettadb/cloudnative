#ldd /home/kunlun/base/program_binaries/kunlun-server-1.0.1/bin/postgres | grep 'not found' | awk -F= '{print $1}' | sort | uniq
for i in `ldd /home/kunlun/base/program_binaries/kunlun-server-1.0.1/bin/postgres | grep 'not found' | awk -F= '{print $1}' | sort | uniq`
do
	cp /home/kunlun/base/program_binaries/kunlun-server-1.0.1/lib/deps/$i /home/kunlun/base/program_binaries/kunlun-server-1.0.1/lib/
done
