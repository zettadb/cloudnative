create table t1(a int primary key, b text);
insert into t1 values(1, 'xbox one s');
select * from t1;
update t1 set b = 'xbox series x' where a = 1;
select * from t1 where b = 'xbox series x';
delete from t1 where a = 1;
select * from t1;
drop table t1;
