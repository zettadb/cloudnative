package Hibernate.test;

import org.Hibernate.entity.Person;
import org.Hibernate.utils.HibernateUtils;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.cfg.Configuration;
import org.junit.jupiter.api.Test;

public class insertById {
    @Test
    public void InsertById() {
        Configuration configuration = new Configuration();
        configuration.configure();
        SessionFactory sessionFactory = HibernateUtils.getSessionFactory();
        Session session = sessionFactory.openSession();
        Transaction transaction = session.beginTransaction();
        Person person = new Person();
//        person.setPid(1);
        person.setPname("small_king_eight");
        person.setPage(22123423);
        person.setPsex("male");
        session.saveOrUpdate(person);
        transaction.commit();
        session.close();
        sessionFactory.close();
    }
}
