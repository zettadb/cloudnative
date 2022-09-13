import javax.swing.*;
import javax.swing.plaf.nimbus.State;
import java.sql.*;
import java.util.ArrayList;
import java.util.Arrays;

public class maria {
    static final String user = "abc";
    static final String pass = "abc";
    public static void main(String[] args) throws SQLException{
        Connection connection = null;
        String host = Arrays.toString(args);
        String url = "jdbc:mariadb://192.168.0.113:47003/postgres";
        try{
            Class.forName("org.mariadb.jdbc.Driver");
            connection = DriverManager.getConnection(url,user,pass);
            Statement statement = connection.createStatement();
            ArrayList sqls = new ArrayList();
            sqls.add("drop table if exists maria");
            sqls.add("create table maria(id int primary key, name text)");
            sqls.add("insert into maria values(1,'a'),(2,'b'),(3,'c')");
            sqls.add("select * from maria");
            sqls.add("update maria set name = 'abc' where id = 3");
            sqls.add("select * from maria");
            sqls.add("delete from maria where id = 3");
            sqls.add("select * from maria");
            for (int i = 0; i <= 7; i++){
                String sql = (String) sqls.get(i);
                System.out.println(sql);

                if (sql == "select * from maria"){
                    System.out.println("-----------------");
                    ResultSet rs = statement.executeQuery(sql);
                    while (rs.next()){
                        int a = rs.getInt("id");
                        String b = rs.getString("name");
                        System.out.println("| id=" + a + " | name=" + b + " |\n-----------------");
                    }
                    rs.close();
                }
                else {
                    statement.execute(sql);
                }
            }
            statement.close();
            connection.close();
        }
        catch (SQLException se){
            se.printStackTrace();
        }catch (Exception e){
            e.printStackTrace();
        }
        finally {
            System.out.println("bye");
        }
    }
}
