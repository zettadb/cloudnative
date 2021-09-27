use clap::{App, Arg};
use postgres::{Client, NoTls};

const DEFAULT_HOST: &str = "localhost";
const DEFAULT_PORT: &str = "7999";
const DEFAULT_USER: &str = "abc";
const DEFAULT_PASS: &str = "abc";
const DEFAULT_DB: &str = "postgres";

struct ConnectionArgs {
    pub host: String,
    pub port: String,
    pub user: String,
    pub pass: String,
    pub db: String,
}

fn parse_args() -> ConnectionArgs {
    let matches = App::new("Execute SQL in Postgres")
        .arg(
            Arg::with_name("host")
                .short("h")
                .long("host")
                .value_name("HOSTNAME")
                .default_value(DEFAULT_HOST)
                .help("Sets the host name of PostgreSQL service")
                .takes_value(true),
        )
        .arg(
            Arg::with_name("port")
                .short("p")
                .long("port")
                .value_name("PORT")
                .default_value(DEFAULT_PORT)
                .help("Sets the port of PostgreSQL service")
                .takes_value(true),
        )
        .arg(
            Arg::with_name("user")
                .short("u")
                .long("user")
                .value_name("USERNAME")
                .default_value(DEFAULT_USER)
                .help("Sets the user to log into PostgreSQL")
                .takes_value(true),
        )
        .arg(
            Arg::with_name("pass")
                .long("pass")
                .value_name("PASSWORD")
                .default_value(DEFAULT_PASS)
                .help("Sets the user's password")
                .takes_value(true),
        )
        .arg(
            Arg::with_name("db")
                .short("d")
                .long("database")
                .value_name("DATABASE")
                .default_value(DEFAULT_DB)
                .help("Sets the database to use")
                .takes_value(true),
        )
        .get_matches();

    ConnectionArgs {
        host: matches.value_of("host").unwrap().to_string(),
        port: matches.value_of("port").unwrap().to_string(),
        user: matches.value_of("user").unwrap().to_string(),
        pass: matches.value_of("pass").unwrap().to_string(),
        db: matches.value_of("db").unwrap().to_string(),
    }
}

fn main() {
    let args = parse_args();

    let sqls = [
        "drop table if exists t1;",
        "create table t1(id integer primary key, info text, wt integer);",
        "insert into t1(id,info,wt) values(1, 'record1', 1);",
        "insert into t1(id,info,wt) values(2, 'record2', 2);",
        "update t1 set wt = 12 where id = 1;",
        "select * from t1;",
        "delete from t1 where id = 1;",
        "select * from t1;",
    ];

    let mut client = Client::connect(
        &format!(
            "postgres://{}:{}@{}:{}/{}",
            args.user, args.pass, args.host, args.port, args.db
        ),
        NoTls,
    )
    .unwrap();

    for sql in sqls {
        // 或者使用 let result = client.query(sql, &[]);
        // query 会输出结果，execute 只返回影响的行数
        let result = client.execute(sql, &[]);
        println!("command: {}, res: {:?}", sql, result);
    }
}
