package Hibernate.test.select;

import org.Hibernate.entity.Person;
import org.Hibernate.utils.HibernateUtils;
import org.hibernate.SQLQuery;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.query.NativeQuery;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.List;

public class selectAllBySQLQuery {
    SessionFactory sessionFactory = null;
    Session session = null ;
    Transaction transaction = null;
    @Test
    public void SelectBySQLQuery () {
        try {
            sessionFactory = HibernateUtils.getSessionFactory();
            session = sessionFactory.openSession();
            transaction = session.beginTransaction();
//            1.创建Nativequery对象
//            里面直接写普通的sql语句
            NativeQuery nativeQuery = session.createNativeQuery("select * from person");

//            下面注释的代码块用的是原生数组形式输出的结果
//            2.因为返回的不是一个list，而是一个数组，所以要用数组Object[]来接收
//            List<Object[]> list = nativeQuery.list();
//            3.最后也是用的for循环遍历打印所有的结果，用Arrays.toString来把数组转换成字符串
//            for (Object[] objects : list) {
//                System.out.println(Arrays.toString(objects));
//            }

//            2.使用addEntity方法把所有结果变成对象形式,里面写的是实体类名.class，然后再调用nativeQuery的list方法
            nativeQuery.addEntity(Person.class);
            List<Person> list = nativeQuery.list();
//            3.使用for循环遍历打印所有的结果，这个时候就不用类型转换了
            for (Person person : list) {
                System.out.println(person);
            }


            transaction.commit();
        } catch (Exception e) {
            e.printStackTrace();
            transaction.rollback();
        } finally {
            session.close();
            sessionFactory.close();
        }
    }
}
