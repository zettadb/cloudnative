import pymysql
import sys


def myconn(host, port, sql, opt):
    conn = pymysql.connect(host=host, port=port , database='postgres', user='abc', password='abc')
    cursor = conn.cursor()
    cursor.execute(sql)
    if opt == 'y':
        res = cursor.fetchall()
        print(str(res) + '\n')
    conn.commit()
    cursor.close()
    conn.close()

def myTest(host, port):
    sql = ['drop table if exists mypython_sm;', 
            'create table mypython_sm(a int primary key, b text);',
            "insert into mypython_sm values(1, 'abc'),(2, 'bcd'),(3, 'cde');", 
            "update mypython_sm set b = 'bcd' where a = 1;", 
            "delete from mypython_sm where a = 1;"
            ]

    select = "\nselect * from mypython_sm;"

    num = 0
    for sqls in sql:
        print('========' + sqls + '========')
        myconn(host, int(port), sqls, 'n')
        print('success')

        if num > 1 and num < 5:
            print(select)
            myconn(host, int(port), select, 'y')
        
        num = num + 1

if __name__ == '__main__':
    myTest(sys.argv[1], sys.argv[2])
