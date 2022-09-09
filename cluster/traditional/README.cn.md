# Copyright (c) 2019 ZettaDB inc. All rights reserved.
# This source code is licensed under Apache 2.0 License,
# combined with Common Clause Condition 1.0, as detailed in the NOTICE file.

�������ݿ⼯Ⱥһ������ʹ��˵��

��˵�����������ʹ��һ�����������м�Ⱥ�İ�װ��������ֹͣ���Լ����������ù���������һ̨
Linux����������ָ�������ã������ݿ⼯Ⱥ�ĸ����ڵ�(�洢�ڵ�Ⱥ������ڵ�Ⱥ����Ⱥ����ڵ㣩
��װ��ָ����Ŀ������ϣ����Ҵ�ü�Ⱥ���ù��߻���ֹͣ��Ⱥ������������Ⱥ���Լ�����������Ⱥ��

����Ҫ��:
1 ���нڵ����ڻ�����ΪLinux, ��װ��bash, sed, gzip, python2�ȹ��߻��߿⡣python 2��ִ�г�������Ϊpython2
2 ���м�Ⱥ�ڵ����ڻ����Ѿ���ȷ���ú��û����ڵ㽫�Ը��û����������û��ܹ�����sudo������Ҫ����.
3 ���߻���ʹ��sshͨ��Ĭ�϶˿ڵ�¼�ڵ����ڻ�����������Ҫ�������롣����������������'ssh login without password'
4 ���ڰ�װ�洢�ڵ�Ļ�������ҪԤ�Ȱ�װ���¿�(�˴�Ϊubuntu 20.04): libncurses5 libaio-dev python-setuptools
5 ���ڰ�װ����ڵ�Ļ�������ҪԤ�Ȱ�װ���¿�(�˴�Ϊubuntu 20.04): libncurses5 libicu66 python-setuptools gcc
6 ���ڰ�װ��������ҪԤ�Ƚ������Ʒ����� (��0.9.2Ϊ����������Ϊ: kunlun-storage-0.9.2.tgz, kunlun-server-0.9.2.tgz,
   kunlun-cluster-manager-0.9.2.tgz ) ���뵱ǰĿ¼. ���⣬�������л����ͽڵ����ڻ��������粻��̫������Ϊ��Ҫ�����������ݵ���Щ�����ϡ�

�ļ�����:
��ǰĿ¼����Ҫ�������ļ�:
 - ���ڰ�װ��������Ҫ�з�����(��0.9.2Ϊ��, ������Ϊ: kunlun-storage-0.9.2.tgz��kunlun-server-0.9.2.tgz��kunlun-cluster-manager-0.9.2.tgz),
   �û����Դ�downloads.zettadb.com������Щ�������������Ѿ������İ汾����Щ��λ��releases�Ķ�Ӧ�汾��(0.8.4�Ժ�)���Ӧ�汾��release-binaries��Ŀ¼��(0.8.3����ǰ); 
   �����ڵ�ǰ���ڿ�����δ�����İ汾����Щ��λ��: http://downloads.zettadb.com/dailybuilds/enterprise
 - �����ļ�(����install.json),
   ��Ҫ�������ýڵ����ϸ��Ϣ�������ڵ����ڻ�������װ�ڵ����õ��û������Լ��ڵ����е���Ϣ�ȡ������ʽ������ϸ˵����
 - ����Ϊ������ص��ļ���ʹ�õĻ��������ǣ��ȸ��������ļ�������ʵ�����е�shell�ű����������иýű�������ɶ�����

�����÷�:
  python2 generate_scripts.py --action=install|stop|start|clean --config=config_file [--defuser=user_to_be_used] [--defbase=basedir_to_be_used]
  bash $action/commands.sh   # ����$action=install|stop|start|clean

˵��:
�ù��߼�ʹ��һ��python�ű� 'generate_scripts.py' ��һ��json��ʽ�������ļ�������ʵ�ʵİ�װ��������(commands.sh),
����������Щ�������м��������ָ���Ķ�����

* ���� --action=������ָ����Ҫִ�еĶ�����Ϊinstall, stop, start, clean ����֮һ

* ���� --config=�ļ���ָ�������ļ���

* ���� '--defuser=user_to_be_used'
���ü�Ⱥ��Ĭ���û��������û��ĳ�������ã���û�������(machines������)��û���û��������ã����Ĭ���û�������ʹ�á�
���û�и�ѡ���Ĭ���û���Ϊ���нű����ڻ����ĵ�ǰ�û�����

* ���� '--defbase=basedir_to_be_used'
���ü�Ⱥ��Ĭ�Ϲ���Ŀ¼�����û��ĳ�������ã����߸û�������(machines, ����)��û�й���Ŀ¼�����ã���Ĭ�Ϲ���Ŀ¼����ʹ�á�
��ѡ����Ŀ¼����Ϊ����·�������û�и�ѡ���'/kunlun'����ΪĬ�ϵĹ���Ŀ¼��
��Ŀ¼�����ڴ�ŷ���������ѹ��ķ��������Լ�һЩ�����ļ��͸����ű��ļ��ȡ�

ʾ��:

1 ��װ��Ⱥ install:
  # ʹ��install.json��Ϊ�����ļ���ʹ��klundb(�ǵ�ǰ�û�)��Ϊ��ȺĬ���û���, /kunlun��Ϊ��ȺĬ�Ϲ���Ŀ¼
  kunlun@kunlun-test2:~$python2 generate_scripts.py --action=install --config=install.json --defuser=klundb
  kunlun@kunlun-test2:~$bash install/commands.sh

2 ֹͣ��Ⱥ stop:
  # ʹ��install.json��Ϊ�����ļ���/home/kunlun/programs��Ϊ��ȺĬ�Ϲ���Ŀ¼��kunlun(��ǰ�û�)��Ϊ��ȺĬ���û�
  kunlun@kunlun-test2:~$python2 generate_scripts.py --action=stop --config=install.json --defbase=/home/kunlun/programs
  kunlun@kunlun-test2:~$bash stop/commands.sh

3 ������Ⱥ start:
  # ʹ��install.json��Ϊ�����ļ���/kunlun��Ϊ��ȺĬ�Ϲ���Ŀ¼��kunlun(��ǰ�û�)��Ϊ��ȺĬ���û�
  kunlun@kunlun-test2:~$python2 generate_scripts.py --action=start --config=install.json
  kunlun@kunlun-test2:~$bash start/commands.sh

4 ����Ⱥ(ֹͣ��Ⱥ����ɾ�����а�װ�Ľڵ㼰����) clean:
  # ʹ��install.json��Ϊ�����ļ���/kunlun��Ϊ��ȺĬ�Ϲ���Ŀ¼��wtz(��ǰ�û�)��Ϊ��ȺĬ���û�
  wtz@kunlun-test2:~$python2 generate_scripts.py --action=clean --config=install.json
  wtz@kunlun-test2:~$bash clean/commands.sh

�����ļ�˵��:

���ڲ�ͬ�Ķ������������������ļ�������������ͬ����һ�㶼ʹ��install�����������ļ�������Ŀ¼�ṹ�����أ�
Ҫ��start/stop/clean�����ļ�Ⱥ��Ҳ��ʹ�øù��ߵ�install�������������ġ�

�����ļ���Ϊ���󲿷֣���ѡ��machines���֣���cluster���֡�
* machines�������ýڵ����ڻ�������Ϣ����Ҫ�������û����ϵ�Ĭ�Ϲ���Ŀ¼, ʹ�õ�Ĭ���û�����ÿ��machine��Ŀ����˵������:
  {
    "ip":"192.168.0.110",   # ������IP
    "basedir":"/kunlun",  # �û�����Ĭ�Ϲ���Ŀ¼
    "user":"kunlun"  # �ڸû���ִ�ж�����Ĭ���û���
  }
* cluster���������ü�Ⱥ����Ϣ����Ⱥ��Ϣ��Ϊ�岿��
  - name: ��Ⱥ���֣�һ��ʹ����ĸ�����ֵ����
  - meta: Ԫ���ݼ�Ⱥ����Ϣ
  - comp: ����ڵ㼯����Ϣ
  - data: ���ݽڵ㼯����Ϣ
  - clustermgr: ��Ⱥ����ڵ����Ϣ(ֻ��Ҫһ��)
* Ԫ���ݼ�ȺΪһ���洢�ڵ㸴���飬һ���౸���ڲ�����2����2������(һ�㽨��>=3������)�Ĵ洢�ڵ㡣
* ���ݽڵ㼯Ϊ����洢�ڵ㸴���飬һ�������鼴Ϊһ�����ݷ�Ƭ��ÿ���������ڲ�����2����2������(һ�㽨��>=3������)�洢�ڵ㡣
* ����ڵ㼯Ϊһ���������ڵ㣬�ǿͻ��˵Ľ���㡣������ȡ������Ҫ�Ľ������Ŀ��

����ÿ���洢�ڵ㣬����mysql-8.0.26������ һ����Ҫ������Ϣ:
   {
     "is_primary":true,  # �Ƿ�Ϊ�������еĳ�ʼ���ڵ㣬һ�����������ҽ���һ�����ڵ㣬��install��Ҫ
     "ip":"192.168.0.110", # �ڵ����ڻ�����ip
     "port":6001, # mysql port
     "xport":60010, # mysql xport����install��Ҫ
     "mgr_port":60011, # ����mysql group replicationͨ�ŵĽڵ㣬��install��Ҫ
     "innodb_buffer_pool_size":"64MB", # innodb��buffer pool��С�����Ի�������Сһ�㣬��������һ����Ҫ��һЩ����install��Ҫ
     "data_dir_path":"/data1", # mysql����Ŀ¼����install��Ҫ
     "log_dir_path":"/data1/log", # mysql binlog����������־�ȵĴ��λ�ã���install��Ҫ
     "innodb_log_dir_path": "/data2/innodblog", # mysql innodb log���λ�ã�����û�У����û�����ã�
                                                # ��Ĭ����log_dir_pathָ����Ŀ¼�£���install�õ�
     "user":"kunlun", # ����mysql���������̵��û���һ��Ӧ����machines����Ķ�Ӧ��Ŀʹ����ͬ��ֵ����install��Ҫ
     "election_weight":50 mysql group replication��ѡ��Ȩ�ء�һ��50���ɣ���install��Ҫ
  }

����ÿ������ڵ㣬����postgresql-11.5������һ����Ҫ������Ϣ:
    {
       "id":1,   # ���ֱ�ʶ��ÿ���ڵ��費�ã�һ���1��ʼ����install��Ҫ��
       "name":"comp1",  # ����, ÿ���ڵ��費ͬ���������Ӽ��ɣ���install��Ҫ��
       "ip":"192.168.0.110", # �ڵ����ڻ�����IP�����ڿͻ�������
       "port":5401, # �˿ڣ����ڿͻ�������
       "user":"abc", # �û��������ڿͻ������ӣ���install��Ҫ��
       "password":"abc", # ���룬���ڿͻ������ӣ���install��Ҫ��
       "datadir":"/pgdatadir" # �ڵ�İ�װĿ¼�����ڴ�Žڵ����ݡ���install��Ҫ��
    }

���ڼ�Ⱥ����ڵ㣬ֻ��Ҫһ����Ϣ:
* ip: �ڵ����ڻ�����IP

�������ÿ��Բ���ʾ��:install.json.

��Ⱥ��װ�������󣬿���ͨ������ڵ���ʼ�Ⱥ�����и���֧�ֵ����ݲ���������ڵ㶼����PostgreSQL-11.5������
���Կ���ͨ��postgresqlЭ�������Ӽ���ڵ㣬�������ֲ������󡣱������ṩ��һ���򵥵Ĳ��ԣ�����֤
��Ⱥ���Ӻͽ���ð�̲���, ���÷�ʽ����:

kunlun@kunlun-test:cluster$ psql -f smokeTest.sql postgres://user:password@ip:port/postgres

�����û��������룬ip���˿���Ҫ��Ϊ��Ӧ�ļ���ڵ����õ����ݡ�

smokeTest.sql�����ص�ַΪ: https://gitee.com/zettadb/cloudnative/blob/main/smoke/smokeTest.sql
