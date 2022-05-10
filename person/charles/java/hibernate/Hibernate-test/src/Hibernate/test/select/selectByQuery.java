package Hibernate.test.select;

import org.Hibernate.entity.Person;
import org.Hibernate.utils.HibernateUtils;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.query.Query;
import org.junit.jupiter.api.Test;

import java.util.List;

public class selectByQuery {
    SessionFactory sessionFactory = null ;
    Session session = null ;
    Transaction transaction = null ;
    @Test
    public void SelectByQuery() {
        try {
            sessionFactory = HibernateUtils.getSessionFactory();
            session = sessionFactory.openSession();
            transaction = session.beginTransaction();
//            第一步：先创建一个Query对象
//            里面的hql语句就是from加对象类名，对象名分大小写
            Query query = session.createQuery("from Person");
//            然后使用query里面的list方法来获取一个列表
            List<Person> list = query.list();
//            最后使用for循环来遍历列表
            for (Person person : list) {
                System.out.println(person);
            }

            transaction.commit();
        } catch (Exception e){
            e.printStackTrace();
            transaction.rollback();
        } finally {
            session.close();
            sessionFactory.close();
        }

    }
}
