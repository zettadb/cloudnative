using System;
using System.Collections.Generic;
using System.Data;
using MySql.Data.MySqlClient;
using System.Text;

namespace mysql
{
    class Program
    {
        static void Main(string[] args)
        {
		//server=127.0.0.1;port=3306;user=root;password=root; database=minecraftdb;
            	string cs = "server=" + args[0] + ";user=abc;password=abc;port=" + args[1] + ";database=postgres";
                Console.WriteLine("testing mysql: " + cs);
		
		MySqlConnection conn = null;
		conn = new MySqlConnection(cs);
		//conn.Open();
		
		//Console.WriteLine("drop table if exists mycs_sm;");
		//MySqlCommand cmd = new MySqlCommand("drop table if exists mycs_sm;", conn);
		//int n = cmd.ExecuteNonQuery();

		List<string> sqlList = new List<string>();
		sqlList.Add("drop table if exists mycs_sm;");
		sqlList.Add("create table mycs_sm(a int primary key, b text);");
		sqlList.Add("insert into mycs_sm values(1,'abc'),(2,'bcd'),(3,'cde');");
		sqlList.Add("select * from mycs_sm;");
		sqlList.Add("update mycs_sm set b = 'def' where a = 1;");
		sqlList.Add("select * from mycs_sm;");
		sqlList.Add("delete from mycs_sm where a = 3;");
		sqlList.Add("select * from mycs_sm;");

		foreach (string i in sqlList){
			Console.WriteLine(i);
			List<string> list = new List<string>();
			if (i == "select * from mycs_sm;"){
				conn.Open();
				MySqlCommand cmd = new MySqlCommand(i, conn);
				MySqlDataReader reader = cmd.ExecuteReader();
				while (reader.Read()){
					string id = reader.GetString("a");
					string name = reader.GetString("b");
					Console.WriteLine(id + " : " + name);
				}
				conn.Close();
			}
			else {
				conn.Open();
				MySqlCommand cmd = new MySqlCommand(i, conn);
				cmd.ExecuteNonQuery();
				conn.Close();
			}
		}

		//conn.Close();
        }
    }
}
