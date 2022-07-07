use mysql::*;
use mysql::prelude::*;
//use std::env;
use clap::{App, Arg};

fn main() {
    let matches = App::new("Execute SQL in Postgres")
        .arg(
            Arg::with_name("host")
                .short("h")
                .long("host")
                .value_name("HOSTNAME")
                .help("Sets the host name of PostgreSQL service")
                .takes_value(true),
        )
        .arg(
           Arg::with_name("port")
                .short("p")
                .long("port")
                .value_name("PORT")
                .help("Sets the port of PostgreSQL service")
                .takes_value(true),
        ).get_matches();
    let host = matches.value_of("host").unwrap_or("192.168.0.113").to_string();
    let port = matches.value_of("port").unwrap_or("5662").to_string();
    let front = "mysql://pgx:pgx_pwd@".to_string();

    let hosts = front + &host + ":" + &port + "/mysql";
    let url = hosts.to_string();
    // let mut hosts = front + &host + ":".to_string() + &port + "/mysql".to_string();
//    let mut url = format!("mysql://pgx:pgx_pwd@{:?}:{:?}/mysql", host, port);
    
    let urls = "mysql://abc:abc@192.168.0.113:5662/postgres";
    println!("{}", url);
    println!("{}", urls);
    let pool = Pool::new(urls).unwrap(); // 获取连接池
    let mut conn = pool.get_conn().unwrap();// 获取链接

    let sql = [
        "drop table if exists myrs_sm;",
        "create table myrs_sm(a int primary key, b text);",
        "insert into myrs_sm values(1, 'abc'),(2,'bcd'),(3,'cde');",
        "select * from myrs_sm;",
        "update myrs_sm set b = 'def' where a = 1",
        "select * from myrs_sm;",
        "delete from myrs_sm where a = 3",
        "select * from myrs_sm;"
    ];

    let selects = "select * from myrs_sm;";
    
    for sqls in sql{
        conn.query_iter(sqls).unwrap();
        println!();
        println!("{:?}", sqls);
        if sqls == "select * from myrs_sm;"{
            conn.query_iter(selects).unwrap()
                .for_each(|row|{
                let r:(i32,String)=from_row(row.unwrap());
                println!("result: a={},b='{}'",r.0,r.1);
            });
        }
    }
}
