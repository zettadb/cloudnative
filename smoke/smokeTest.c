/*
 * Copyright (c) 2019 ZettaDB inc. All rights reserved.
 * This source code is licensed under Apache 2.0 License,
 * combined with Common Clause Condition 1.0, as detailed in the NOTICE file.
 *
 * src/test/examples/testlibpq.c
 *
 * testlibpq.c
 *
 * Test the C version of libpq, the PostgreSQL frontend library.
 */
#include <stdio.h>
#include <stdlib.h>
#include "libpq-fe.h"

static void
exit_nicely(PGconn *conn)
{
	PQfinish(conn);
	exit(1);
}

int
main(int argc, char **argv)
{
	const char *conninfo;
	PGconn	   *conn;
	PGresult   *res;
	int			nFields;
	int			i,
				j;

	/*
	 * If the user supplies a parameter on the command line, use it as the
	 * conninfo string; otherwise default to setting dbname=postgres and using
	 * environment variables or defaults for all other connection parameters.
	 */
	if (argc > 1)
		conninfo = argv[1];
	else
		conninfo = "dbname = postgres host=192.168.0.104 port=6401 user=abc password=abc";

	/* Make a connection to the database */
	conn = PQconnectdb(conninfo);

	/* Check to see that the backend connection was successfully made */
	if (PQstatus(conn) != CONNECTION_OK)
	{
		fprintf(stderr, "Connection to database failed: %s",
				PQerrorMessage(conn));
		exit_nicely(conn);
	}

	/* Set always-secure search path, so malicous users can't take control. */
	res = PQexec(conn, "SET client_min_messages TO 'warning';");
	PQclear(res);
	res = PQexec(conn, "drop table if exists t1");
	if (PQresultStatus(res) != PGRES_COMMAND_OK)
	{
		fprintf(stderr, "drop table failed: %s", PQerrorMessage(conn));
		PQclear(res);
		exit_nicely(conn);
	} else {
		fprintf(stderr, "drop table ok\n");
	}
	PQclear(res);
	res = PQexec(conn, "RESET client_min_messages;");
	PQclear(res);
	/*
	 * Our test case here involves using a cursor, for which we must be inside
	 * a transaction block.  We could do the whole thing with a single
	 * PQexec() of "select * from pg_database", but that's too trivial to make
	 * a good example.
	 */

	/* Start a transaction block */
	res = PQexec(conn, "create table t1(id integer primary key,info text, wt integer)");
	if (PQresultStatus(res) != PGRES_COMMAND_OK)
	{
		fprintf(stderr, "create table command failed: %s", PQerrorMessage(conn));
		PQclear(res);
		exit_nicely(conn);
	} else {
		fprintf(stderr, "create table ok\n");
	}
	PQclear(res);

	/*
	 * Fetch rows from pg_database, the system catalog of databases
	 */
	res = PQexec(conn, "insert into t1(id,info,wt) values(1, 'record1', 1)");
	if (PQresultStatus(res) != PGRES_COMMAND_OK)
	{
		fprintf(stderr, "insert record 1 failed: %s", PQerrorMessage(conn));
		PQclear(res);
		exit_nicely(conn);
	} else {
		fprintf(stderr, "insert record 1 ok\n");
	}
	PQclear(res);

	res = PQexec(conn, "insert into t1(id,info,wt) values(2, 'record2', 2)");
	if (PQresultStatus(res) != PGRES_COMMAND_OK)
	{
		fprintf(stderr, "insert record 2 failed: %s", PQerrorMessage(conn));
		PQclear(res);
		exit_nicely(conn);
	} else {
		fprintf(stderr, "insert record 2 ok\n");
	}
	PQclear(res);

	res = PQexec(conn, "update t1 set wt = 12 where id = 1");
	if (PQresultStatus(res) != PGRES_COMMAND_OK)
	{
		fprintf(stderr, "update record failed: %s", PQerrorMessage(conn));
		PQclear(res);
		exit_nicely(conn);
	} else {
		fprintf(stderr, "update record ok\n");
	}
	PQclear(res);

	res = PQexec(conn, "delete from t1 where id = 1");
	if (PQresultStatus(res) != PGRES_COMMAND_OK)
	{
		fprintf(stderr, "delete record failed: %s", PQerrorMessage(conn));
		PQclear(res);
		exit_nicely(conn);
	} else {
		fprintf(stderr, "delete record ok\n");
	}
	PQclear(res);

	res = PQexec(conn, "drop table t1");
	if (PQresultStatus(res) != PGRES_COMMAND_OK)
	{
		fprintf(stderr, "drop table failed: %s", PQerrorMessage(conn));
		PQclear(res);
		exit_nicely(conn);
	} else {
		fprintf(stderr, "drop table ok\n");
	}
	PQclear(res);

	/* close the connection to the database and cleanup */
	PQfinish(conn);

	return 0;
}
