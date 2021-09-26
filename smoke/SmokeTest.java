package kunlun.test;

/*
 * Copyright (c) 2019 ZettaDB inc. All rights reserved.
 * This source code is licensed under Apache 2.0 License,
 * combined with Common Clause Condition 1.0, as detailed in the NOTICE file.
 */

import java.io.BufferedReader;
import java.io.FileReader;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.LinkedList;
import java.util.List;
import java.util.Properties;

public class SmokeTest {

    static {
        try {
            Class.forName("org.postgresql.Driver");
            //Class.forName("com.mysql.cj.jdbc.Driver");
        } catch (Exception ex) {
        }
    }

    public static Connection getConnection(String user,
                                           String password,
                                           String host,
                                           int port,
                                           String dbname) {
        String proto = "postgresql";
        Properties props = new Properties();
        props.setProperty("user", user);
        props.setProperty("password", password);
        String url = "jdbc:" + proto+"://" + host + ":" + port + "/" + dbname;
        try {
            return DriverManager.getConnection(url, props);
        } catch (Exception ex) {
            ex.printStackTrace();
            return null;
        }
    }

    public static void smokeTest(Connection conn) throws Exception{
        boolean autocommit = conn.getAutoCommit();
        System.out.println("default autocommit: " + autocommit);
        conn.setAutoCommit(true);
        Statement st =conn.createStatement();
	st.execute("SET client_min_messages TO 'warning';");
        st.execute("drop table if exists t1;");
	st.execute("RESET client_min_messages;");
        String createSql = "create table t1(id integer primary key, " +
                           "info text, wt integer);";
        st.execute(createSql);
        st.execute("insert into t1(id,info,wt) values(1, 'record1', 1);");
        st.execute("insert into t1(id,info,wt) values(2, 'record2', 2);");
        st.execute("update t1 set wt = 12 where id = 1;");
        ResultSet res1 = st.executeQuery("select * from t1;");
        System.out.printf("res1:%s%n", showResults(res1).toString());
        res1.close();
        st.close();

        String pstr = "select * from t1 where id=?";
        PreparedStatement ps = conn.prepareStatement(pstr);
        ps.setInt(1, 1);
        ResultSet pres = ps.executeQuery();
        System.out.printf("pres1:%s%n", showResults(pres).toString());
        ps.setInt(1, 2);
        pres = ps.executeQuery();
        System.out.printf("pres2:%s%n", showResults(pres).toString());
        ps.close();

        pstr = "update t1 set info=? , wt=? where id=?";
        ps = conn.prepareStatement(pstr);
        ps.setString(1, "Rec1");
        ps.setInt(2, 2);
        ps.setInt(3, 1);
        ps.execute();
        ps.setString(1, "Rec2");
        ps.setInt(2, 3);
        ps.setInt(3, 2);
        ps.execute();
        ps.close();

        st =conn.createStatement();
        ResultSet res2 = st.executeQuery("select * from t1;");
        System.out.printf("res2:%s%n", showResults(res2).toString());
        res2.close();
        st.execute("delete from t1 where id = 1;");
        ResultSet res3 = st.executeQuery("select * from t1;");
        System.out.printf("res3:%s%n", showResults(res3).toString());
        res3.close();
        st.execute("drop table t1;");
        st.close();
        conn.setAutoCommit(autocommit);
    }

    /*
     * We do the following actions:
     * 1 Create the able
     * 2 Insert two records
     * 3 Update the first record.
     * 4 Query the records(res1).
     * 5 Delete the second record.
     * 6 Query the records again(res2).
     * 7 Drop the table.
     */
    public static void smokeTestFile(Connection conn, String cmdfile) throws Exception{
        boolean autocommit = conn.getAutoCommit();
        System.out.println("default autocommit: " + autocommit);
        conn.setAutoCommit(true);
        Statement st =conn.createStatement();
        BufferedReader br = new BufferedReader(new FileReader(cmdfile));
        String cmd = null;
        do {
            cmd = br.readLine();
            if (cmd == null) {
                break;
            }
            if (cmd.toUpperCase().startsWith("SELECT")) {
                ResultSet res = st.executeQuery(cmd);
                System.out.printf("sql:%s, res:%s%n", cmd,
                                  showResults(res).toString());
                res.close();
            } else {
                st.execute(cmd);
            }
        } while (cmd != null);
        br.close();
        st.close();
        conn.setAutoCommit(autocommit);
    }

    private static List<List<String>> showResults(ResultSet res)
        throws Exception {
        LinkedList<List<String>> results = new LinkedList<>();
        int cols = res.getMetaData().getColumnCount();
        while (res.next()) {
            List<String> row = new ArrayList<>(cols);
            for (int i = 0; i < cols; i++) {
                row.add(res.getString(i + 1));
            }
            results.addLast(row);
        }
        return results;
    }

    public static void test1(String[] args) throws Exception{
        String host = args[0];
        int port = Integer.valueOf(args[1]);
        String user = "abc";
        String password = "abc";
        String database = "postgres";
        Connection conn = getConnection(user, password, host, port, database);
        smokeTest(conn);
        conn.close();
    }

    public static void main(String[] args) throws Exception {
        test1(args);
    }
}
