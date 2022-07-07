// g++ mysql.cpp -lmysqlcppconn -o mysqltest
// ./mysqltest "tcp://192.168.0.113:5661"
#include "mysql_connection.h"
#include <stdlib.h>
#include <iostream>
#include <cppconn/driver.h>
#include <cppconn/exception.h>
#include <cppconn/resultset.h>
#include <cppconn/statement.h>
using namespace std;
int main(int argc,char* argv[]){
 	sql::Driver *driver;
  	sql::Connection *con;
  	sql::Statement *stmt;
  	sql::ResultSet *res;

  /* Create a connection */
  	driver = get_driver_instance();
	//string infos = sprintf("\"tcp://" , argv[1] , "\"");
	//string in1 = "\"tcp://";
	//string in2 = "\"";
	//string infos = in1 + argv[1] + in2;
	string infos = argv[1];
  	con = driver->connect(infos, "abc", "abc");
	con->setSchema("postgres");
	stmt = con->createStatement();
  	stmt->execute("drop table if exists mycpp_sm;");
	cout<<"drop table if exists mycpp_sm;"<<endl;
	stmt->execute("create table mycpp_sm(a int primary key, b text)");
	cout<<"create table mycpp_sm(a int primary key, b text)"<<endl;
	stmt->execute("insert into mycpp_sm values(1, 'abc'),(2,'bcd'),(3,'cde')");
	cout<<"insert into mycpp_sm(1, 'abc'),(2,'bcd'),(3, 'cde')"<<endl;
	stmt->executeQuery("select * from mycpp_sm");
	cout<<"select * from mycpp_sm"<<endl;
	stmt->execute("update mycpp_sm set b = 'qwer' where a = 2");
	cout<<"update mycpp_sm set b = 'qwer' where a = 2"<<endl;
	stmt->executeQuery("select * from mycpp_sm");
	cout<<"select * from mycpp_sm"<<endl;
        stmt->execute("delete from mycpp_sm where a = 3");
	cout<<"delete from mycpp_sm where a = 3"<<endl;
	stmt->executeQuery("select * from mycpp_sm");
	cout<<"select * from mycpp_sm"<<endl;
	delete stmt;
	delete con;
}
