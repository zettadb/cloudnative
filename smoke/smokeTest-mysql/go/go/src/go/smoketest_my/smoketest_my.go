
package main

import (
    "fmt"
    _ "github.com/go-sql-driver/mysql"
    "github.com/jmoiron/sqlx"
    "flag"
)

func checkError(err error) {
        if err != nil {
                panic(err)
        }
}

func main() {
        var User string
        var Pwd string
        var Host string
        var Port int
        var Dbname string
        flag.StringVar(&Host,"h","","默认为空")
        flag.IntVar(&Port,"p",5001,"默认为5001")
        flag.StringVar(&Pwd,"pwd","abc","默认为abc")
        flag.StringVar(&Dbname,"d","postgres","默认为postgres")
        flag.StringVar(&User,"u","abc","默认为abc")
        flag.Parse()

        fmt.Println("============= Golang-mysql ============")
        // Initialize connection string.
        var connectionString string = fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8", User, Pwd, Host, Port, Dbname)

        // Initialize connection object.
        db, err := sqlx.Open("mysql", connectionString)
        checkError(err)

        err = db.Ping()
        checkError(err)
        fmt.Println("Successfully connection to database!!!")

        // Drop previous table of same name if one exists.
        _, err = db.Exec("drop table if exists mygo_sm;")
        checkError(err)
        fmt.Println("Successfully drop   table")

        // Create table.
        _, err = db.Exec("create table mygo_sm(id int primary key,name text,gender text);")
        checkError(err)
        fmt.Println("Successfully create table")

        // Insert some data into table.
//        sql_statement := "insert into mygo_sm values ($1, $2, $3);"
        _, err = db.Exec("insert into mygo_sm values( 1, 'banana', 'male')")
        checkError(err)
        _, err = db.Exec("insert into mygo_sm values(2, 'orange', 'female')")
        checkError(err)
        _, err = db.Exec("insert into mygo_sm values(3, 'apple', 'male')")
        checkError(err)
        fmt.Println("Successfully insert table")

        _, err = db.Exec("delete from mygo_sm where id = 2")
        checkError(err)
        fmt.Println("Successfully delete table")

        _, err = db.Exec("update mygo_sm set name = 'update' where id = 3")
        checkError(err)
        fmt.Println("Successfully update table")

        _, err = db.Exec("select * from mygo_sm")
        checkError(err)
        fmt.Println("Successfully select table")

        fmt.Println("=================================")
}

