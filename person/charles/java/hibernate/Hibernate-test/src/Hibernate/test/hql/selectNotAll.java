package Hibernate.test.hql;

import org.Hibernate.entity.Person;
import org.Hibernate.utils.HibernateUtils;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.query.Query;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.List;
import java.util.Objects;

public class selectNotAll {
    SessionFactory sessionFactory = null ;
    Session session = null ;
    Transaction transaction = null ;

    @Test
    public void SelectNotAll() {
        try {
            sessionFactory = HibernateUtils.getSessionFactory();
            session = sessionFactory.openSession();
            transaction = session.beginTransaction();

            String hql1 = "select new Person(pid,pname) from Person";
            Query query = session.createQuery(hql1);
            List<Person> list  = query.list();
            for (Person object : list) {
                System.out.println(object);
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
