// ubuntu环境： sudo apt-get install libmysql++-dev -y
// 这两个是看情况安装：sudo apt-get install mysql-server mysql-client -y
// 在ubuntu 上编译：gcc -I/usr/include/mysql -L/usr/lib/mysql mysql.c -lmysqlclient -o mysql
// /usr/include/mysql /usr/lib/mysql 这两个位置是不一定的，可以通过wehereis mysql来看,查看/path/include/mysql 和 /path/lib/mysql这两个
// 运行：./mysql host port
#include <stdio.h>
#include <mysql.h>

int main(int argc,char** argv){
	printf("connect to %s:%s\n",argv[1], argv[2]);
	printf("version: %s\n", mysql_get_client_info());
	MYSQL* my = mysql_init(NULL);
	int port = atoi(argv[2]);

	if(!mysql_real_connect(my, ("%s", argv[1]), "abc", "abc", "postgres", port, NULL, 0)){
		printf("connect error !\n");
		mysql_close(my);
	}

	printf("drop table if exists myc_sm;\n");
	mysql_query(my, "drop table if exists myc_sm;");
	
	printf("create table myc_sm;\n");
	mysql_query(my, "create table myc_sm(a int primary key, b text);");

	printf("insert into myc_sm values(1,'abc'),(2,'bcd'),(3,'cde')\n");
	mysql_query(my, "insert into myc_sm values(1,'abc'),(2,'bcd'),(3,'cde')");
	
	void select(void)
	{
		printf("\n\nselect * from myc_sm;\n");
		int res = mysql_query(my, "select * from myc_sm;");
		MYSQL_RES* a = mysql_store_result(my);
		int rows = mysql_num_rows(a);
		int cols = mysql_num_fields(a);
		printf("rows: %d, cols: %d\n", rows, cols);
		MYSQL_FIELD *field = mysql_fetch_fields(a);
		for(int i = 0; i < cols; i++)
		{
			printf("%-10s\t", field[i].name);
		}
		puts("");
  		MYSQL_ROW line;
	  	for(int i = 0; i < rows; i++)
  		{
	      		line =  mysql_fetch_row(a);
      			for(int j = 0; j < cols; j++)
      			{
          			printf("%-10s\t", line[j]);
	      		}
      			puts("");
	  	}
	}
	
	select();

	printf("update myc_sm set b = 'def' where a = 1;");
	mysql_query(my, "update myc_sm set b = 'def' where a = 1;");
	select();

	printf("delete from myc_sm where a = 3;");
	mysql_query(my, "delete from myc_sm where a = 3;");
	select();

	mysql_close(my);
}
