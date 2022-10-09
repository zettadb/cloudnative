using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Npgsql;

namespace SmokeTest
{
    class Program
    {
        static void Main(string[] args)
        {
	    string host = args[0];
	    string port = args[1];
            Console.WriteLine("\n========== C# Driver ============");
            string connSting = "Host=" + host + ";Port=" + port + ";Username=abc;Password=abc;Database=postgres";
            var conn = new NpgsqlConnection(connSting);
            
            NpgsqlDataAdapter DA = new NpgsqlDataAdapter();
            //NpgsqlCommand cmd_select = new NpgsqlCommand("select * from SmokeTestTable_csharp");
            //DA.SelectCommand = cmd_select;
            
            
            

            string drop1 = "drop table if exists SmokeTestTable_csharp;";
            string create = "create table SmokeTestTable_csharp(id int primary key,name text,gender text);";
            string insert = "insert into SmokeTestTable_csharp values(1,'li','male'),(2,'delete_me','male'),(3,'update_me','female');";
            string create2 = "create table testfordelete(id int primary key);";
            string droptab = "drop table testfordelete;";
            string delete = "delete from Smoketesttable_csharp where id = 2";
            string update = "update SmokeTestTable_csharp set name = 'update' where id = 3";
            string select = "select * from SmokeTestTable_csharp";
            string drodb = "drop database if exists smoketestdb;";
            string commit = "commit;";
            string credb = "create database smoketestdb;";
            string swdb = "use smoketestdb";
            string dropdb = "drop database smoketestdb;";



            conn.Open();
            
            using (var com1 = new NpgsqlCommand(drop1, conn)) 
            using (var com2 = new NpgsqlCommand(create, conn)) 
            using (var com3 = new NpgsqlCommand(insert, conn)) 
            using (var com4 = new NpgsqlCommand(create2, conn)) 
            using (var com5 = new NpgsqlCommand(droptab, conn)) 
            using (var com6 = new NpgsqlCommand(delete, conn))
            using (var com7 = new NpgsqlCommand(update, conn))
            using (var com8 = new NpgsqlCommand(select, conn))
            using (var drobd1 = new NpgsqlCommand(drodb,conn))
            using (var credb1 = new NpgsqlCommand(credb, conn))
            using (var swdb1 = new NpgsqlCommand(swdb, conn))
            using (var dropdb1 = new NpgsqlCommand(dropdb, conn))
            using (var comm = new NpgsqlCommand(commit,conn))

            {
                
                //drobd1.ExecuteNonQuery();
                //Console.WriteLine("drop table success!");
                //credb1.ExecuteNonQuery();
                //Console.WriteLine("create database success!");
                //comm.ExecuteNonQuery();
                //Console.WriteLine("commit success!");
                //swdb1.ExecuteNonQuery();
                //Console.WriteLine("switch database success!");

                com1.ExecuteNonQuery();
                Console.WriteLine("drop   table success!");
                com2.ExecuteNonQuery();
                Console.WriteLine("create table success!");
                com3.ExecuteNonQuery();
                Console.WriteLine("insert table success!");
                com4.ExecuteNonQuery();
                Console.WriteLine("create table success!");
                com5.ExecuteNonQuery();
                Console.WriteLine("drop   table success!");
                com6.ExecuteNonQuery();
                Console.WriteLine("delete table success!");
                com7.ExecuteNonQuery();
                Console.WriteLine("update table success!");
                com8.ExecuteNonQuery();
                Console.WriteLine("select table success!");
                comm.ExecuteNonQuery();
                Console.WriteLine("commit table success!");
                //dropdb1.ExecuteNonQuery();
                //Console.WriteLine("drop database success!");
            }
            conn.Close();
            Console.WriteLine("=================================\n");
        }
    }
}
