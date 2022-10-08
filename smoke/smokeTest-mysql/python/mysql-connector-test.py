import argparse
from time import sleep
from mysql import connector
def test(sql, host, port, user, pwd, db):
    conn = connector.connect(buffered=True, host=host, port=port, user=user, passwd=pwd, database=db, ssl_disabled=True)
    cur = conn.cursor()

    print(sql)
    if sql == 'select * from mysql_connector_python;':
        cur.execute(sql)
        cur.autocommit = false
        rs = cur.fetchall()
        srs = str(rs)
        srs = srs.replace('[(', '')
        srs = srs.replace(')]', '')
        srs = srs.replace('), (', '\n------\n')
        srs = srs.replace(',', ' |')
        srs = srs.replace('\'', '')
        print('--------\na | b\n------\n' + srs + '\n--------')
    else:
        cur.execute(sql)
    
    conn.commit()
    cur.close()
    conn.close()

def execSql(host, port, user, pwd, db):
    sql = ['drop table if exists mysql_connector_python;',
            'create table mysql_connector_python(a int primary key, b text);',
            "insert into mysql_connector_python values(1,'a'),(2,'b'),(3,'c');",
            'select * from mysql_connector_python;',
            "update mysql_connector_python set b = 'abc' where a = 3;",
            'select * from mysql_connector_python;',
            'delete from mysql_connector_python where a = 3;',
            'select * from mysql_connector_python;']
    for sqls in sql:
        test(sqls, host, port, user, pwd, db)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'this script is use to test ddl replication!')
    parser.add_argument('--host', help='host')
    parser.add_argument('--port', default=3306, help='port')
    parser.add_argument('--db', default='postgres', help='database name')
    parser.add_argument('--pwd', default='abc', help='password')
    parser.add_argument('--user', default='abc', help='user name')
    args = parser.parse_args()
    host = args.host
    port = args.port
    db   = args.db
    pwd  = args.pwd
    user = args.user
    
    print(host, str(port))
    execSql(host, port, user, pwd, db)
