<?php
$host = "$argv[1]";
$port = "$argv[2]";
$dbname = "postgres";
$user = "abc";
$pwd = "abc";

$conn = mysqli_connect($host, $user, $pwd, $dbname, $port) or die("数据库连接错误！");

$sql1 = "drop table if  exists myphp_sm \n";
$sql2 = "create table if not exists myphp_sm(a int primary key, b text)\n";
$sql3 = "insert into myphp_sm values (1,'abc')\n";
$sql4 = "select * from myphp_sm\n";
$sql5 = "update myphp_sm set b = 'asd' where a = 1\n";
$sql6 = "select * from myphp_sm\n";
$sql7 = "delete from myphp_sm where a = 1\n";

$rs = mysqli_query($conn, $sql1);
echo "$sql1 success\n";

$rs = mysqli_query($conn, $sql2);
echo "$sql2 success\n";

$rs = mysqli_query($conn, $sql3);
echo "$sql3 success\n";

$rs = mysqli_query($conn, $sql4);
echo "$sql4 success\n";
$row = mysqli_fetch_array($rs);
var_dump($row);

$rs = mysqli_query($conn, $sql5);
echo "$sql5 success\n";

$rs = mysqli_query($conn, $sql6);
echo "$sql6 success\n";
$row = mysqli_fetch_array($rs);
var_dump($row);

$rs = mysqli_query($conn, $sql7);
echo "$sql7 success\n";
?>

