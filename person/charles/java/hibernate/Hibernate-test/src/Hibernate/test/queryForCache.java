package Hibernate.test;

import org.Hibernate.entity.Person;
import org.Hibernate.utils.HibernateUtils;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.cfg.Configuration;
import org.junit.jupiter.api.Test;

public class queryForCache {
    @Test
    public void doubleQuery() {
        Configuration configuration = new Configuration();
        configuration.configure();
        SessionFactory sessionFactory = HibernateUtils.getSessionFactory();
        Session session = sessionFactory.openSession();
//        这个时候已经默认打开了一级缓存了
        Transaction transaction = session.beginTransaction();
        Person person = session.get(Person.class,3);
//        在这一步会对持久化对象person的id值3与一级缓存区进行对比查看是否有相同的对象，如果没有就去数据库进行查询操作
        System.out.println(person);
        person.setPname("king_eight_egg");
        Person person1 = session.get(Person.class,3);
//        再查询一次的时候发现在一级缓存区有相同的id为3的数据，则直接读取一级缓存区的数据，不会访问数据库
        System.out.println(person1);
        transaction.commit();
        session.close();
        sessionFactory.close();
    }
}
