package Hibernate.test.hql;

import org.Hibernate.entity.Person;
import org.Hibernate.utils.HibernateUtils;
import org.hibernate.Filter;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.query.Query;
import org.junit.jupiter.api.Test;

import javax.transaction.UserTransaction;
import java.util.List;

public class selectWhere {
    SessionFactory sessionFactory = null ;
    Session session = null ;
    Transaction transaction = null ;
    @Test
    public void SelectWhere () {
        try {
            sessionFactory = HibernateUtils.getSessionFactory();
            session = sessionFactory.openSession();
            transaction = session.beginTransaction();

//            Query query = session.createQuery("from Person where pid = 3");
//            Query query = session.createQuery("from Person where pname = 'small_king_eight' and page = 22");
//            先创建一个Query对象，里面的占位符第一个是?0，第二个占位符是?1，以此类推
//            Query query = session.createQuery("from Person where pname = ?0 and page =
            Query query = session.createQuery("from Person where pname like ?0");
//            然后是设置对应占位符的参数
//            分别有两个参数
//                    第一个参数是占位符的位置
//                    第二个参数是具体的值
            query.setParameter(0,"%king%");
//            query.setParameter(1,22);
//            接着是和之前一样把结果返回一个列表出来
            List<Person> list = query.list();
//            然后用for循环去遍历结果
            for (Person person : list) {
                System.out.println(person.getPid() + "::" + person.getPname());
            }

            transaction.commit();
        } catch (Exception e ) {
            e.printStackTrace();
            transaction.rollback();
        }finally {
            session.close();
            sessionFactory.close();
        }
    }
}
