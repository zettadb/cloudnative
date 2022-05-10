package Hibernate.test;

import org.Hibernate.entity.Person;
import org.Hibernate.utils.HibernateUtils;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.junit.jupiter.api.Test;

public class addByTry {
    @Test
    public void Test() {
        SessionFactory sessionFactory = null;
//        因为现在通过线程绑定了session，所以就不用我们自己去新建一个session了。
        Session session = null;
        Transaction transaction =null;
        //如果不把对应的返回对象给提取出来，则这些对象只能在Try里面运行
        try {
            sessionFactory = HibernateUtils.getSessionFactory();
//            session = sessionFactory.openSession(); 原语句
//            因为我们绑定了session并返回了一个方法，所以现在我们直接调用这个方法就行。
            session = HibernateUtils.getCurrentObject();
            transaction = session.beginTransaction();
            Person person = session.get(Person.class,3);
            person.setPname("bigs_huang");

//            int i = 10/0;
//            0不可以为除数，所以这一步一定会失败
            transaction.commit();
            //如果上面的成功了就直接commit
        } catch(Exception e) {
            transaction.rollback();
//            如果不成功就会走roolback
        } finally {
//            不管怎么样最后都会去关闭session 和sessionFactory,这样就可以防止失败的时候没有关闭导致浪费资源
            session.close();
            sessionFactory.close();
//            现在绑定了之后sessionFactory也不用我们自己关闭了，本来完整的项目就不用我们频繁的关闭
        }
    }
}
