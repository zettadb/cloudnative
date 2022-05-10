package Hibernate.test;

import org.Hibernate.entity.Person;
import org.Hibernate.utils.HibernateUtils;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.cfg.Configuration;
import org.junit.jupiter.api.Test;

public class selectById {
    @Test
    public void selectById() {
        Configuration configuration = new Configuration();
        configuration.configure();
        SessionFactory sessionFactory = HibernateUtils.getSessionFactory();
        Session session = sessionFactory.openSession();
        Transaction transaction = session.beginTransaction();
//        查询使用的是session的get方法
//        第一个参数是 对象类.class
//        第二个参数是 对应的主键值
        Person person = session.get(Person.class,3);
        System.out.println(person);
        person.setPname("king_eight_egg");
        session.saveOrUpdate(person);
        transaction.commit();
        session.close();
        sessionFactory.close();
    }
}