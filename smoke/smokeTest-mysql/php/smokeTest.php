<?php
/*
 * Copyright (c) 2019 ZettaDB inc. All rights reserved.
 * This source code is licensed under Apache 2.0 License,
 * combined with Common Clause Condition 1.0, as detailed in the NOTICE file.
 */

function showresults($ret) {
	echo "=== select results ===\n";
	while ($row = pg_fetch_row($ret)) {
		$str="";
		foreach ($row as $item){
			$str .= $item."  ";
		}
		echo "row: $str\n";
	}
}

function checkret($db, $cmd, $ret) {
	if (!$ret) {
		echo $cmd.pg_last_error($db)."\n";
		exit(1);
	} else {
		echo $cmd.":success\n";
	}
}

$host = "host=$argv[1]";
$port = "port=$argv[2]";
$dbname = "dbname=postgres";
$credentials = "user=abc password=abc";
$connstr="$host $port $dbname $credentials";

echo "conn string: $connstr\n";

$db = pg_connect($connstr);
if(!$db){
	echo "Error : Unable to open database\n";
	exit(1);
} else {
	echo "Opened database successfully\n";
}

$sql = "SET client_min_messages TO 'warning';";
$ret = pg_query($db, $sql);
checkret($db, $sql, $ret);

$sql = "drop table if exists t1;";
$ret = pg_query($db, $sql);
checkret($db, $sql, $ret);

$sql = "RESET client_min_messages;";
$ret = pg_query($db, $sql);
checkret($db, $sql, $ret);

$sql = "create table t1(id integer primary key, info text, wt integer);";
$ret = pg_query($db, $sql);
checkret($db, $sql, $ret);

$sql = "insert into t1(id,info,wt) values(1, 'record1', 1);";
$ret = pg_query($db, $sql);
checkret($db, $sql, $ret);

$sql = "insert into t1(id,info,wt) values(2, 'record2', 2);";
$ret = pg_query($db, $sql);
checkret($db, $sql, $ret);

$sql = "update t1 set wt = 12 where id = 1;";
$ret = pg_query($db, $sql);
checkret($db, $sql, $ret);

$sql = "select * from t1;";
$ret = pg_query($db, $sql);
echo("$sql: $ret\n");
showresults($ret);

$sql = 'select * from t1 where id=$1';
$ret = pg_prepare($db, "prep", $sql);
checkret($db,  "prep:".$sql, $ret);

$ret = pg_execute($db, "prep", array(1));
showresults($ret);

$ret = pg_execute($db, "prep", array(2));
showresults($ret);

$sql = 'update t1 set info=$1 , wt=$2 where id=$3';
$ret = pg_prepare($db, "prep2", $sql);
checkret($db, "prep:".$sql, $ret);

$ret = pg_execute($db, "prep2", array('Rec1', 2, 1));
checkret($db, "prep2:{Rec1,2,1}", $ret);

$ret = pg_execute($db, "prep2", array('Rec2', 3, 2));
checkret($db, "prep2:{Rec2,3,2}", $ret);

$sql = "select * from t1;";
$ret = pg_query($db, $sql);
echo("$sql: $ret\n");
showresults($ret);

$sql = "delete from t1 where id = 1;";
$ret = pg_query($db, $sql);
checkret($db, $sql, $ret);

$sql = "select * from t1;";
$ret = pg_query($db, $sql);
echo("$sql: $ret\n");
showresults($ret);

pg_close($db)
?>
