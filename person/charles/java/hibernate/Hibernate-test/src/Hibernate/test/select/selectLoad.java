package Hibernate.test.select;

import org.Hibernate.entity.Person;
import org.Hibernate.utils.HibernateUtils;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.junit.jupiter.api.Test;

public class selectLoad {
    SessionFactory sessionFactory = null ;
    Session session = null ;
    Transaction transaction = null ;
    @Test
    public void SelectLoad() {
        try {
            sessionFactory = HibernateUtils.getSessionFactory();
            session = sessionFactory.openSession();
            transaction = session.beginTransaction();
            Person person = session.load(Person.class,1);
            person.getPid();
            person.getPname();
            System.out.println(person.getPid() + "::" + person.getPname());
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
