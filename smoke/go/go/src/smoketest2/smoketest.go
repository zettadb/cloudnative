package main

import (
	"database/sql"
	"fmt"
	"flag"
	_ "github.com/lib/pq"
)

const (
	// Initialize connection constants.
	//HOST     = "mydemoserver.postgres.database.azure.com"
	//DATABASE = "postgres"
	//USER     = "abc"
	//PASSWORD = "abc"
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
	var Db string
	flag.StringVar(&Host,"h","","默认为空")
	flag.IntVar(&Port,"p",5001,"默认为5001")
	flag.StringVar(&Pwd,"pwd","abc","默认为abc")
	flag.StringVar(&Db,"d","postgres","默认为postgres")
	flag.StringVar(&User,"u","abc","默认为abc")
	flag.Parse()

	fmt.Println("============= Golang ============")
	// Initialize connection string.
	var connectionString string = fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable", Host, Port,User,Pwd,Db)

	// Initialize connection object.
	db, err := sql.Open("postgres", connectionString)
	checkError(err)

	err = db.Ping()
	checkError(err)
        fmt.Println("Successfully connection to database!!!")

	// Drop previous table of same name if one exists.
	_, err = db.Exec("drop table if exists SmokeTestTable_go;")
	checkError(err)
	fmt.Println("Successfully drop   table")

	// Create table.
	_, err = db.Exec("create table SmokeTestTable_go(id int primary key,name text,gender text);")
	checkError(err)
	fmt.Println("Successfully create table")

	// Insert some data into table.
	sql_statement := "insert into SmokeTestTable_go values ($1, $2, $3);"
	_, err = db.Exec(sql_statement, 1, "banana", "male")
	checkError(err)
	_, err = db.Exec(sql_statement, 2, "orange", "female")
	checkError(err)
	_, err = db.Exec(sql_statement, 3, "apple", "male")
	checkError(err)
	fmt.Println("Successfully insert table")

	_, err = db.Exec("delete from Smoketesttable_csharp where id = 2")
        checkError(err)
        fmt.Println("Successfully delete table")

        _, err = db.Exec("update SmokeTestTable_go set name = 'update' where id = 2")
        checkError(err)
        fmt.Println("Successfully update table")

	_, err = db.Exec("select * from SmokeTestTable_go")
        checkError(err)
        fmt.Println("Successfully select table")
	
	fmt.Println("=================================")
}
