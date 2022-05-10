package Hibernate.test;

import org.Hibernate.entity.Person;
import org.Hibernate.utils.HibernateUtils;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.cfg.Configuration;
import org.junit.jupiter.api.Test;

public class PersonTest {
    @Test
    public void addPerson() {
//        step 1 : 加载hibernate的核心配置文件,hibernate会默认在src下面去找hibernate.cfg.xml文件
        Configuration cfg = new Configuration();
        cfg.configure();

//        step 2: 创建SessionFactory对象，读取hibernate的核心配置文件内容，创建SessionFactory
//        在这个过程中，根据映射关系会在数据库里面把表创建好
//        SessionFactory sessionFactory = cfg.buildSessionFactory(); 这个是没有生成工具类之前的语句
        SessionFactory sessionFactory = HibernateUtils.getSessionFactory(); //这个是已经生成工具类的语句

//        step 3 : 使用SessionFactory创建session对象
        Session session = sessionFactory.openSession();

//        step 4 ： 开启事务
        Transaction tx = session.beginTransaction();

//        step 5 : curd操作
        Person person = new Person();
        person.setPid(2);
        person.setPage(20);
        person.setPname("small_king_eight");
        person.setPsex("male");


//        会话完成后要记得把数据保存到session里，不然不会被执行
        session.save(person);


//        step 6 : commit
        tx.commit();

//        step 7 ： 关闭会话
        session.close();
//        sessionFactory.close();
    }
    @Test
    public void updatebyId() {
        Configuration configuration = new Configuration();
        configuration.configure();
        SessionFactory sessionFactory = HibernateUtils.getSessionFactory();
        Session session = sessionFactory.openSession();
        Transaction transaction = session.beginTransaction();
        Person person = session.get(Person.class,2);
        person.setPage(18);
        person.setPname("big_king_eight");
        session.update(person);
        transaction.commit();
        session.close();
//        sessionFactory.close();
    }
    @Test
    public void deletebyId() {
        Configuration configuration = new Configuration();
        configuration.configure();
        SessionFactory sessionFactory = HibernateUtils.getSessionFactory();
        Session session = sessionFactory.openSession();
        Transaction transaction = session.beginTransaction();
        Person person = session.get(Person.class,2);
        session.delete(person);
        transaction.commit();
        session.close();
        sessionFactory.close();
    }
    @Test
    public void selectbyId() {
        Configuration configuration = new Configuration();
        configuration.configure();
        SessionFactory sessionFactory = HibernateUtils.getSessionFactory();
        Session session = sessionFactory.openSession();
        Transaction transaction = session.beginTransaction();
        Person person = session.get(Person.class,1);
        System.out.println(person);
        transaction.commit();
        session.close();
//        sessionFactory.close();
    }
}