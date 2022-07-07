// 使用process获取命令行传的参数
var arguments = process.argv.splice(2);
var hosts = arguments[0];
var ports  = arguments[1];

var mysql  = require('mysql');

var connection = mysql.createConnection({
    host     : hosts,
    user     : 'abc',
    password : 'abc',
    port: ports,
    database: 'postgres'
});
//console.log(connection)


connection.connect();

var sql1 = 'drop table if exists myjs_sm';
var sql2 = 'create table if not exists myjs_sm(a int primary key,b text);'
var sql3 = 'insert into myjs_sm values(1,"abc")';
var sqls = 'select * from myjs_sm';
var sql4 = 'update myjs_sm set b = "asd" where a = 1';
var sql5 = 'delete from myjs_sm where a = 1';

var  execsql=function(arg1){
//查
	connection.query(arg1, function (err, result) {
    		if(err){
        	console.log(err.message);
        	return;
    	}

    	console.log('-----------------------[ "' + arg1 + '" ]');
    	console.log(result);
    	console.log('------------------------------------------------------------\n\n');
	});

	//connection.end();
}

execsql(sql1);
execsql(sql2);
execsql(sql3);
execsql(sqls);
execsql(sql4);
execsql(sqls);
execsql(sql5);
connection.end();
