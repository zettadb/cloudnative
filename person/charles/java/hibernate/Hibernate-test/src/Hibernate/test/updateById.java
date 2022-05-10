package Hibernate.test;

import org.Hibernate.entity.Person;
import org.Hibernate.utils.HibernateUtils;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.cfg.Configuration;
import org.junit.jupiter.api.Test;

public class updateById {
    @Test
    public void UpdateById() {
        Configuration configuration = new Configuration();
        configuration.configure();
        SessionFactory sessionFactory = HibernateUtils.getSessionFactory();
        Session session = sessionFactory.openSession();
        Transaction transaction = session.beginTransaction();
        Person person = session.get(Person.class,1);
        System.out.println(person);
        person.setPname("big1_king_eight");
        session.update(person);
        //session.save(person);
        System.out.println(person);
        transaction.commit();
        session.close();
        sessionFactory.close();
    }
}
