package Hibernate.test.hql;

import org.Hibernate.entity.Person;
import org.Hibernate.utils.HibernateUtils;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.query.Query;
import org.junit.jupiter.api.Test;

import java.util.List;

public class selectAll {
    SessionFactory sessionFactory = null ;
    Session session = null ;
    Transaction transaction = null ;
    @Test
    public void SelectAll(){
        try {
            sessionFactory = HibernateUtils.getSessionFactory();
            session = sessionFactory.openSession();
            transaction = session.beginTransaction();
            Query query = session.createQuery("from Person");
            List<Person> list = query.list();
            for (Person person : list){
                System.out.println(person.getPsex()+ "--" + person.getPid() + "--" + person.getPname());
            }
//            for (Person person : list) {
//                System.out.println(person);
//            }
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
