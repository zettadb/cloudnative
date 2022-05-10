package Hibernate.test.hql;

import org.Hibernate.entity.Person;
import org.Hibernate.utils.HibernateUtils;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.query.Query;
import org.junit.jupiter.api.Test;

import java.util.List;

public class selectLimit {
    SessionFactory sessionFactory = null ;
    Session session = null ;
    Transaction transaction = null ;
    @Test
    public void SelectLimtit() {
        try {
            sessionFactory = HibernateUtils.getSessionFactory();
            session = sessionFactory.openSession();
            transaction = session.beginTransaction();
//            先查询所有的结果
            Query query = session.createQuery("from Person");
//            然后再用setFirstResult设置从第几个结果开始
            query.setFirstResult(0);
//            再用setMaxResults设置从第几个结果结束
            query.setMaxResults(3);
            //其它的就和之前一样了
            List<Person> list  = query.list();
            for (Person person : list) {
                System.out.println(person.getPid() + "::" + person.getPname());
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
