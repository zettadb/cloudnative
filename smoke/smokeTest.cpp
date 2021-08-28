/*
 * Copyright (c) 2019 ZettaDB inc. All rights reserved.
 * This source code is licensed under Apache 2.0 License,
 * 
 * sudo apt install libpq-dev
 * git clone https://github.com/jtv/libpqxx.git
 * cd libpqxx
 * ./configure
 * make
 * sudo make install
 *
 * g++ -o smokeTest smokeTest.cpp -lpqxx -lpq -std=c++17
 * ./smokeTest "dbname = postgres host=127.0.0.1 port=5401 user=abc password=abc"
 *
 * Test the C++ version of libpqxx, the PostgreSQL frontend library.
 */
#include <iostream>
#include <pqxx/pqxx>

using namespace std;
using namespace pqxx;

int
main(int argc, char **argv)
{
	const char *conninfo;

	if (argc > 1)
		conninfo = argv[1];
	else
		conninfo = "dbname = postgres user=abc password=abc hostaddr=127.0.0.1 port=5401";
	
	try{
		pqxx::connection db(conninfo);
		if (db.is_open()) {
			cout << "Opened database successfully: " << db.dbname() << endl;
		} else {
			cout << "Can't open database" << endl;
			return 1;
		}

		pqxx::nontransaction txn1{db};
		txn1.exec("drop table if exists t1");
		txn1.exec("create table t1(id integer primary key, info text, wt integer)");
		txn1.commit();

		pqxx::work txn2{db};
		txn2.exec("insert into t1(id,info,wt) values(1, 'record1', 1)");
		txn2.exec("insert into t1(id,info,wt) values(2, 'record2', 2)");
		txn2.exec("insert into t1(id,info,wt) values(3, 'record3', 3)");
		txn2.exec("update t1 set wt = 12 where id = 1");
		txn2.exec("delete from t1 where id = 2");

		pqxx::result r2{txn2.exec("select * from t1")};
		for (auto row: r2)
			std::cout << row[0] << " " << row[1] << " " << row[2] << std::endl;
	
		txn2.commit();
		
		pqxx::nontransaction txn3{db};
		txn3.exec("drop table t1");
		txn3.commit();

		db.close();
	}catch (const std::exception &e){
		cerr << e.what() << std::endl;
		return 1;
	}
	
	return 0;
}
