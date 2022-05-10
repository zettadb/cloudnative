package org.Hibernate.utils;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.cfg.Configuration;

public class HibernateUtils {

//    把cfg 和 sessionFactory提取出来，否则后续的方法不可以使用静态代码块里的api
    static Configuration cfg = null;
    static SessionFactory sessionFactory = null;

//    静态代码块的实现
    static {
//        加载核心配置文件
    cfg = new Configuration();
    cfg.configure();
    sessionFactory = cfg.buildSessionFactory();
    }

    public static Session getCurrentObject() {
        return sessionFactory.getCurrentSession();
    }

//    提供一个方法getSessionFactory
    public static SessionFactory getSessionFactory() {
//        因为无法直接return sessionFactory,所以要把静态代码块里面Configuation和SessionFactory给捞取出来
        return sessionFactory;
    }
}
