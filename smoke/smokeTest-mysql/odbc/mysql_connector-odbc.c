// 编译：gcc mysql_connector-odbc.c -o mysql_connector-odbc -lmysqlclient -L/usr/lib64/mysql
// 	如果-lmysqlclient提示找不到这个连接库，用locate mysqlclient命令找到对应的位置然后使用-L选项指定连接库的路径
// 使用：./mysql_connector-odbc -h 192.168.100.0 -p 12345 -d testdb
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <mysql/mysql.h>
#include <unistd.h>
#include <getopt.h>

MYSQL *conn_ptr;
MYSQL_RES *res_ptr;
MYSQL_ROW sqlrow;
unsigned int timeout = 7;	//超时时间7秒

void dispaly_row(MYSQL *ptr)
{
	unsigned int field_count = 0;
	while(field_count<mysql_field_count(ptr)) //返回在结果结合中字段的数目
	{
		printf("%s",sqlrow[field_count]);
		field_count++;
	}
	printf("\n");
}

void display_header()
{
	MYSQL_FIELD *field_ptr;
	printf("Column details:\n");
	while((field_ptr = mysql_fetch_field(res_ptr))!= NULL)//返回列的定义字段信息
	{
		printf("\t Name:%s\n",field_ptr->name);
		printf("\t Type:");
		if(IS_NUM(field_ptr->type))//若字段类型为数字
		{
			printf("Numeric field\n");
		}
		else
		{
			switch(field_ptr->type)
			{
				case FIELD_TYPE_VAR_STRING:
					printf("VACHAR\n");
					break;
				case FIELD_TYPE_LONG:
					printf("LONG\n");
					break;
				default:
					printf("Type is %d,check in mysql_com.h\n",field_ptr->type);
			}
		}
		printf("\t Max width %ld \n",field_ptr->length);
		if(field_ptr->flags & AUTO_INCREMENT_FLAG)
			printf("\t Auto increments\n");
		printf("\n");
	}
}

int connect_str(char *connect_sql)
{
        int ret = 0;
	if(conn_ptr)
        {
                ret = mysql_query(conn_ptr,connect_sql);
                printf("%s\n", connect_sql);
                if(!ret)
                {
                        res_ptr = mysql_use_result(conn_ptr);
                        if(res_ptr)
                        {
                                display_header();
                                printf("Retrieved %lu rows\n",(unsigned long)mysql_num_rows(res_ptr));//在结果集合中返回行的数量
                                while((sqlrow = mysql_fetch_row(res_ptr)))//返回store_result中得到的结构体，并从中检索单行
                                {
                                        dispaly_row(conn_ptr);
                                }
                        }

                        if(mysql_errno(conn_ptr))
                        {
                                printf("Connect Erro:%d %s\n",mysql_errno(conn_ptr),mysql_error(conn_ptr));//返回错误代码、错误消息
                                return -2;
                        }

                        mysql_free_result(res_ptr);
                }
                else
                {
                        printf("Connect Erro:%d %s\n",mysql_errno(conn_ptr),mysql_error(conn_ptr));//返回错误代码、错误消息
                        return -3;
                }

        }
        else    //错误处理
        {
                printf("Connection Failed!\n");
                if(mysql_errno(conn_ptr))
                {
                        printf("Connect Erro:%d %s\n",mysql_errno(conn_ptr),mysql_error(conn_ptr));//返回错误代码、错误消息
                }
                return -2;
        }

        return 0;

}
int main(int argc, char* argv[])
{
	char *HOST, *PORT;
	char *cDB = NULL;
	int option_index;
	int ret, res = 0;
	int first_row = 1;

	static struct option long_option[] = {
		{"port", 1, NULL, 'p'},
		{"host", 1, NULL, 'h'},
		{"db", 1, NULL, 'd'},
		{"help", 0, NULL, 0},
		{0, 0, 0, 0}
	};

	static char* const short_option = (char*)"p:h:d:";
	
	while((res=getopt_long(argc, argv, short_option, long_option, &option_index))!=-1)
	{
		switch(res)
		{
			case 'p':
				PORT = optarg;
				break;
			case 'h':
				HOST = optarg;
				break;
			case 'd':
				cDB = optarg;
				break;
			case '?':
				puts("usage:\n	--help\n	-p/--port=port, \n	-h/--host=host,\n	-d/--db=database_name");
				exit(0);
		}
	}
	if(HOST == NULL || HOST == NULL || cDB == NULL)
	{
		puts("usage:\n	--help\n	-p=port || --port=port\n	-h=host || --host=host\n	-d=database_name || --db=database_name");
		exit(0);
	}
	int iPort = atoi(PORT);
	printf("your host is %s, port is %d, database is %s\n", HOST, iPort, cDB);

        conn_ptr = mysql_init(NULL);//初始化
        if(!conn_ptr)
        {
                printf("mysql_init failed!\n");
                return -1;
        }

        ret = mysql_options(conn_ptr,MYSQL_OPT_CONNECT_TIMEOUT,(const char*)&timeout);//设置超时选项
        if(ret)
        {
                printf("Options Set ERRO!\n");
        }
        conn_ptr = mysql_real_connect(conn_ptr,HOST,"abc","abc",cDB,iPort,NULL,0);//连接MySQL testdb数据库
	puts("Connection Succeed!");

	connect_str("drop table if exists test");//使用connct_str函数操作数据库
	connect_str("create table test(a int)");
	connect_str("insert into test values (1), (2), (3)");
	connect_str("select * from test");
	connect_str("update test set a = 5 where a = 3");
	connect_str("select * from test");
	connect_str("delete from test where a = 5");
        connect_str("select * from test");

	mysql_close(conn_ptr);
        printf("Connection closed!\n");

	return 0;
}
