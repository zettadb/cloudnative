const { findSourceMap } = require('module');
const { CLIENT_RENEG_LIMIT } = require('tls');
const pg=require('./node_modules/pg');
var conString = "postgres://abc:abc@192.168.0.113:5401/postgres";
var client = new pg.Client(conString);

client.connect(function(err){
    if(err){
        return console.error('数据库连接出错',err);
    }
    
    console.log("")
    console.log("=========== JS Driver ==============");
    client.query('drop table if exists smoketesttable_js;',function(err,data){
        if(err){
            return console.error('step 1 : droped table failed!',err);
            
        }else{
            console.log('step 1 : drop table success!')
        }
    })
	client.query('drop table if exists smoketesttable_js1;');//再运行一次的原因是因为如果失败了就只有一个failed!提示，没有报错信息。所以再运行一次让这个报错信息显示出来

    client.query('create table smoketesttable_js(id int primary key,name text,gender text);',function(err,data){
        if(err){
            return console.error('step 2 : create failed!',err);
        }else{
            console.log('step 2 : create table success!')
        }
    })
	client.query('create table smoketesttable_js1(id int primary key,name text,gender text);')

    client.query("insert into smoketesttable_js values(1,'name1','male'),(2,'name2','female'),(3,'name3','male');",function(err,data){
        if(err){
            return console.error('step 3 : insert failed!',err);
        }else{
            console.log('step 3 : insert data success!')
        }
    })
	client.query("insert into smoketesttable_js1 values(1,'name1','male'),(2,'name2','female'),(3,'name3','male');")

    client.query("delete from smoketesttable_js where id = 1;",function(err){
        if(err){
            return console.error('step 4 : delete failed!')
        }else{
            console.log("step 4 : delete data success!")
        }
    })
	client.query("delete from smoketesttable_js1 where id = 1;")

    client.query("update smoketesttable_js set gender = 'male' where id = 2;",function(err){
        if(err){
            return console.error("step 5 : update failed!")
        }else{
            console.log('step 5 : update gender success!')
        }
    })
	client.query("update smoketesttable_js1 set gender = 'male' where id = 2;")

    
    client.query("select * from smoketesttable_js;",function(err){
        if(err){
            return console.error("select failed!")
            client.query("step 6 : select * from smoktesttable_js;")
        }else{
            console.log('step 6 : select table success!')
        }
    })
    client.query("select * from smoketesttable_js1;")

    client.query("commit",function(err){
        if(err){
            return console.error("select failed!")
        }else{
            console.log('step 6 : commit success!')
        }
        client.end();
        console.log("====================================");
	console.log("")
    })


})

