// java -cp mysql-connector-java-8.0.16.jar mysql.java host:port
//like : java -cp mysql-connector-java-8.0.16.jar mysql.java 192.168.0.113:5661
// 目前在ubuntu上能运行，centos8不行。如126上是可以的
import java.sql.DriverManager;
import java.util.ArrayList;
import java.sql.*;
import java.util.*;

public class mysql {
    // MySQL 8.0 以下版本 - JDBC 驱动名及数据库 URL
    static final String JDBC_DRIVER = "com.mysql.cj.jdbc.Driver";
    // MySQL 8.0 以上版本 - JDBC 驱动名及数据库 URL
    //static final String JDBC_DRIVER = "com.mysql.cj.jdbc.Driver";
    //static final String DB_URL = "jdbc:mysql://localhost:3306/RUNOOB?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC";
    // 数据库的用户名与密码，需要根据自己的设置
    static final String USER = "abc";
    static final String PASS = "abc";

    public static void main(String[] args) {
        Connection conn = null;
        Statement stmt = null;
	
	//处理传入的参数
	String host = Arrays.toString(args);
	String urls1 = "jdbc:mysql://" + host + "/postgres";
	String urls2 = urls1.replace("[","");
	String urls = urls2.replace("]","");
        
	try{
            // 注册 JDBC 驱动
            Class.forName(JDBC_DRIVER);

            // 打开链接
            System.out.println("连接数据库" + host + "...");
            conn = DriverManager.getConnection(urls,USER,PASS);

            // 执行查询
            System.out.println(" 实例化Statement对象...");
            stmt = conn.createStatement();
            ArrayList sqls = new ArrayList();
            sqls.add("drop table if exists myjdbc_sm;");
            sqls.add("create table myjdbc_sm(a int primary key, b text);");
            sqls.add("insert into myjdbc_sm values(1, 'abc'),(2, 'bcd'),(3, 'cde');");
            sqls.add("select * from myjdbc_sm;");
            sqls.add("update myjdbc_sm set b = 'def' where a = 1;");
            sqls.add("select * from myjdbc_sm;");
            sqls.add("delete from myjdbc_sm where a = 3;");
            sqls.add("select * from myjdbc_sm;");

            for (int i = 0; i <= 7; ++i){
                String sql = (String) sqls.get(i);
                System.out.println(sql);

                if (sql == "select * from myjdbc_sm;"){
                    ResultSet rs = stmt.executeQuery(sql);
                    while(rs.next()) {
                        int a = rs.getInt("a");
                        String b = rs.getString("b");
                        System.out.print(" a: " + a + " b: " + b + "\n");
                    }
                    rs.close();
                }
                else {
                    stmt.execute(sql);
                }
            }

            stmt.close();
            conn.close();
        }catch(SQLException se){
            // 处理 JDBC 错误
            se.printStackTrace();
        }catch(Exception e){
            // 处理 Class.forName 错误
            e.printStackTrace();
        }finally{
            // 关闭资源
            try{
                if(stmt!=null) stmt.close();
            }catch(SQLException se2){
            }// 什么都不做
            try{
                if(conn!=null) conn.close();
            }catch(SQLException se){
                se.printStackTrace();
            }
        }
        System.out.println("Goodbye!");
    }
}

