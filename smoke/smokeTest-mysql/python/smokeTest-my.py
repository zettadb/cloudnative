import pymysql
import sys


def myconn(host, port, sql):
    conn = pymysql.connect(host=host, port=port , database='postgres', user='abc', password='abc')
    cursor = conn.cursor()
    cursor.execute(sql)
    cursor.close()
    conn.close()

def myTest(host, port):
    sql = ['drop table if exists mypython_sm', 'create table mypython_sm(a int primary key, b text)',
    "insert into mypython_sm values(1, 'abc')", "update mypython_sm set b = 'bcd' where a = 1",
    "select * from mypython_sm", "delete from mypython_sm where a = 1", "drop table mypython_sm"]

    

    for sqls in sql:
        print(sqls)
        myconn(host, int(port), sqls)
        print('success')

if __name__ == '__main__':
    myTest(sys.argv[1], sys.argv[2])
