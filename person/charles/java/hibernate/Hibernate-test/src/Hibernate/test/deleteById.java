package Hibernate.test;

import org.Hibernate.entity.Person;
import org.Hibernate.utils.HibernateUtils;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.cfg.Configuration;
import org.junit.jupiter.api.Test;

public class deleteById {
    @Test
    public void DeleteById() {
        Configuration configuration = new Configuration();
        configuration.configure();
        SessionFactory sessionFactory = HibernateUtils.getSessionFactory();
        Session session = sessionFactory.openSession();
        Transaction transaction = session.beginTransaction();
        //Person person = session.get(Person.class,2);//和修改操作是一样的，第一步是通过查询get到自己想要的数据
        Person person = new Person();//这个是第二种方法，通过一个新建的对象把对应的id给出来
        person.setPid(1); //设置id为3的数据
        System.out.println(person);

        session.delete(person); //然后是使用session的delete方法
//        session.save(person);
        transaction.commit(); //不管是不是ddl语句最好都是要提交下事务处理
        session.close();
        sessionFactory.close();
    }
}
