-- The foreign test is removed, it is a regular test now.
-- MATCH FULL

--
--
CREATE TABLE PKTABLE ( ptest1 int, ptest2 int, ptest3 text, PRIMARY KEY(ptest1, ptest2) );
CREATE TABLE FKTABLE ( ftest1 int, ftest2 int, ftest3 int);

-- Insert test data into PKTABLE
INSERT INTO PKTABLE VALUES (1, 2, 'Test1');
INSERT INTO PKTABLE VALUES (1, 3, 'Test1-2');
INSERT INTO PKTABLE VALUES (2, 4, 'Test2');
INSERT INTO PKTABLE VALUES (3, 6, 'Test3');
INSERT INTO PKTABLE VALUES (4, 8, 'Test4');
INSERT INTO PKTABLE VALUES (5, 10, 'Test5');

-- Insert successful rows into FK TABLE
INSERT INTO FKTABLE VALUES (1, 2, 4);
INSERT INTO FKTABLE VALUES (1, 3, 5);
INSERT INTO FKTABLE VALUES (2, 4, 8);
INSERT INTO FKTABLE VALUES (3, 6, 12);
INSERT INTO FKTABLE VALUES (NULL, NULL, 0);

-- Insert failed rows into FK TABLE
INSERT INTO FKTABLE VALUES (100, 2, 4);
INSERT INTO FKTABLE VALUES (2, 2, 4);
INSERT INTO FKTABLE VALUES (NULL, 2, 4);
INSERT INTO FKTABLE VALUES (1, NULL, 4);

-- Check FKTABLE
SELECT * FROM FKTABLE;

-- Delete a row from PK TABLE
DELETE FROM PKTABLE WHERE ptest1=1 and ptest2=2;

-- Check FKTABLE for removal of matched row
SELECT * FROM FKTABLE;

-- Delete another row from PK TABLE
DELETE FROM PKTABLE WHERE ptest1=5 and ptest2=10;

-- Check FKTABLE (should be no change)
SELECT * FROM FKTABLE;

-- Update a row from PK TABLE
UPDATE PKTABLE SET ptest1=1 WHERE ptest1=2;

-- Check FKTABLE for update of matched row
SELECT * FROM FKTABLE;

-- Try altering the column type where foreign keys are involved
ALTER TABLE PKTABLE ALTER COLUMN ptest1 TYPE bigint;
ALTER TABLE FKTABLE ALTER COLUMN ftest1 TYPE bigint;
SELECT * FROM PKTABLE;
SELECT * FROM FKTABLE;

DROP TABLE PKTABLE CASCADE;
DROP TABLE FKTABLE;

-- test a tricky case: we can elide firing the FK check trigger during
-- an UPDATE if the UPDATE did not change the foreign key
-- field. However, we can't do this if our transaction was the one that
-- created the updated row and the trigger is deferred, since our UPDATE
-- will have invalidated the original newly-inserted tuple, and therefore
-- cause the on-INSERT RI trigger not to be fired.

CREATE TEMP TABLE pktable (
    id int primary key,
    other int
);

CREATE TEMP TABLE fktable (
    id int primary key,
    fk int
);

INSERT INTO pktable VALUES (5, 10);

BEGIN;

-- doesn't match PK, but no error yet
INSERT INTO fktable VALUES (0, 20);

-- don't change FK
UPDATE fktable SET id = id + 1;

-- should catch error from initial INSERT
COMMIT;

BEGIN;

-- INSERT will be in a subxact
SAVEPOINT savept1;

-- doesn't match PK, but no error yet
INSERT INTO fktable VALUES (0, 20);

--will crash: RELEASE SAVEPOINT savept1;

-- don't change FK
UPDATE fktable SET id = id + 1;

-- should catch error from initial INSERT
COMMIT;

BEGIN;

-- doesn't match PK, but no error yet
INSERT INTO fktable VALUES (0, 20);

-- UPDATE will be in a subxact
SAVEPOINT savept1;

-- don't change FK
UPDATE fktable SET id = id + 1;

-- Roll back the UPDATE
ROLLBACK TO savept1;

-- should catch error from initial INSERT
COMMIT;

--
-- check ALTER CONSTRAINT
--

INSERT INTO fktable VALUES (1, 5);

BEGIN;

-- doesn't match FK, should throw error now
UPDATE pktable SET id = 10 WHERE id = 5;

COMMIT;

BEGIN;

-- doesn't match PK, should throw error now
INSERT INTO fktable VALUES (0, 20);

COMMIT;

-- test order of firing of FK triggers when several RI-induced changes need to
-- be made to the same row.  This was broken by subtransaction-related
-- changes in 8.0.

CREATE TEMP TABLE users (
  id INT PRIMARY KEY,
  name VARCHAR NOT NULL
);

INSERT INTO users VALUES (1, 'Jozko');
INSERT INTO users VALUES (2, 'Ferko');
INSERT INTO users VALUES (3, 'Samko');

CREATE TEMP TABLE tasks (
  id INT PRIMARY KEY,
  owner INT,
  worker INT,
  checked_by INT
);

INSERT INTO tasks VALUES (1,1,NULL,NULL);
INSERT INTO tasks VALUES (2,2,2,NULL);
INSERT INTO tasks VALUES (3,3,3,3);

SELECT * FROM tasks;

UPDATE users SET id = 4 WHERE id = 3;

SELECT * FROM tasks;

DELETE FROM users WHERE id = 4;

SELECT * FROM tasks;

-- could fail with only 2 changes to make, if row was already updated
BEGIN;
UPDATE tasks set id=id WHERE id=2;
SELECT * FROM tasks;
DELETE FROM users WHERE id = 2;
SELECT * FROM tasks;
COMMIT;

--
-- Test self-referential FK with CASCADE (bug #6268)
--
create temp table selfref (
    a int primary key,
    b int);

insert into selfref (a, b)
values
    (0, 0),
    (1, 1);

begin;
    update selfref set a = 123 where a = 0;
    select a, b from selfref;
    update selfref set a = 456 where a = 123;
    select a, b from selfref;
commit;

--
-- Test that SET DEFAULT actions recognize updates to default values
--
create temp table defp (f1 int primary key);
create temp table defc (f1 int default 0);
insert into defp values (0), (1), (2);
insert into defc values (2);
select * from defc;
delete from defp where f1 = 2;
select * from defc;
delete from defp where f1 = 0; -- fail
alter table defc alter column f1 set default 1;
delete from defp where f1 = 0;
select * from defc;
delete from defp where f1 = 1; -- fail

--
-- Test the difference between NO ACTION and RESTRICT
--
create temp table pp (f1 int primary key);
create temp table cc (f1 int);
insert into pp values(12);
insert into pp values(11);
update pp set f1=f1+1;
insert into cc values(13);
update pp set f1=f1+1;
update pp set f1=f1+1; -- fail
drop table pp;
drop table cc;

create temp table pp (f1 int primary key);
create temp table cc (f1 int);
insert into pp values(12);
insert into pp values(11);
update pp set f1=f1+1;
insert into cc values(13);
update pp set f1=f1+1; -- fail
drop table pp;
drop table cc;

--
-- Test interaction of foreign-key optimization with rules (bug #14219)
--
create temp table t1 (a integer primary key, b text);
create temp table t2 (a integer primary key, b integer);

explain (costs off) delete from t1 where a = 1;
delete from t1 where a = 1;

--
-- Test deferred FK check on a tuple deleted by a rolled-back subtransaction
--
create table pktable2(f1 int primary key);
create table fktable2(f1 int);
insert into pktable2 values(1);

begin;
insert into fktable2 values(1);
savepoint x;
delete from fktable2;
rollback to x;
commit;

begin;
insert into fktable2 values(2);
savepoint x;
delete from fktable2;
rollback to x;
commit; -- fail

--
-- Test that we prevent dropping FK constraint with pending trigger events
--
begin;
insert into fktable2 values(2);
commit;

begin;
delete from pktable2 where f1 = 1;
commit;

drop table pktable2;
drop table fktable2;



-- Creation of a partitioned hierarchy with irregular definitions
CREATE TABLE fk_notpartitioned_pk (fdrop1 int, a int, fdrop2 int, b int, PRIMARY KEY (a, b));
ALTER TABLE fk_notpartitioned_pk DROP COLUMN fdrop1, DROP COLUMN fdrop2;
CREATE TABLE fk_partitioned_fk (b int, fdrop1 int, a int) PARTITION BY RANGE (a, b);
ALTER TABLE fk_partitioned_fk DROP COLUMN fdrop1;
CREATE TABLE fk_partitioned_fk_1 (fdrop1 int, fdrop2 int, a int, fdrop3 int, b int);
ALTER TABLE fk_partitioned_fk_1 DROP COLUMN fdrop1, DROP COLUMN fdrop2, DROP COLUMN fdrop3;
ALTER TABLE fk_partitioned_fk ATTACH PARTITION fk_partitioned_fk_1 FOR VALUES FROM (0,0) TO (1000,1000);
CREATE TABLE fk_partitioned_fk_2 (b int, fdrop1 int, fdrop2 int, a int);
ALTER TABLE fk_partitioned_fk_2 DROP COLUMN fdrop1, DROP COLUMN fdrop2;
ALTER TABLE fk_partitioned_fk ATTACH PARTITION fk_partitioned_fk_2 FOR VALUES FROM (1000,1000) TO (2000,2000);

CREATE TABLE fk_partitioned_fk_3 (fdrop1 int, fdrop2 int, fdrop3 int, fdrop4 int, b int, a int)
  PARTITION BY HASH (a);
ALTER TABLE fk_partitioned_fk_3 DROP COLUMN fdrop1, DROP COLUMN fdrop2,
	DROP COLUMN fdrop3, DROP COLUMN fdrop4;
CREATE TABLE fk_partitioned_fk_3_0 PARTITION OF fk_partitioned_fk_3 FOR VALUES WITH (MODULUS 5, REMAINDER 0);
CREATE TABLE fk_partitioned_fk_3_1 PARTITION OF fk_partitioned_fk_3 FOR VALUES WITH (MODULUS 5, REMAINDER 1);
ALTER TABLE fk_partitioned_fk ATTACH PARTITION fk_partitioned_fk_3
  FOR VALUES FROM (2000,2000) TO (3000,3000);

-- these inserts, targetting both the partition directly as well as the
-- partitioned table, should all fail
INSERT INTO fk_partitioned_fk (a,b) VALUES (500, 501);
INSERT INTO fk_partitioned_fk_1 (a,b) VALUES (500, 501);
INSERT INTO fk_partitioned_fk (a,b) VALUES (1500, 1501);
INSERT INTO fk_partitioned_fk_2 (a,b) VALUES (1500, 1501);
INSERT INTO fk_partitioned_fk (a,b) VALUES (2500, 2502);
INSERT INTO fk_partitioned_fk_3 (a,b) VALUES (2500, 2502);
INSERT INTO fk_partitioned_fk (a,b) VALUES (2501, 2503);
INSERT INTO fk_partitioned_fk_3 (a,b) VALUES (2501, 2503);

-- but if we insert the values that make them valid, then they work
INSERT INTO fk_notpartitioned_pk VALUES (500, 501), (1500, 1501),
  (2500, 2502), (2501, 2503);
INSERT INTO fk_partitioned_fk (a,b) VALUES (500, 501);
INSERT INTO fk_partitioned_fk (a,b) VALUES (1500, 1501);
INSERT INTO fk_partitioned_fk (a,b) VALUES (2500, 2502);
INSERT INTO fk_partitioned_fk (a,b) VALUES (2501, 2503);

-- this update fails because there is no referenced row
UPDATE fk_partitioned_fk SET a = a + 1 WHERE a = 2501;
-- but we can fix it thusly:
INSERT INTO fk_notpartitioned_pk (a,b) VALUES (2502, 2503);
UPDATE fk_partitioned_fk SET a = a + 1 WHERE a = 2501;

-- these updates would leave lingering rows in the referencing table; disallow
UPDATE fk_notpartitioned_pk SET b = 502 WHERE a = 500;
UPDATE fk_notpartitioned_pk SET b = 1502 WHERE a = 1500;
UPDATE fk_notpartitioned_pk SET b = 2504 WHERE a = 2500;
-- done.
DROP TABLE fk_notpartitioned_pk;
DROP TABLE fk_partitioned_fk;

-- Test some other exotic foreign key features: MATCH SIMPLE, ON UPDATE/DELETE
-- actions
CREATE TABLE fk_notpartitioned_pk (a int, b int, primary key (a, b));
CREATE TABLE fk_partitioned_fk (a int default 2501, b int default 142857) PARTITION BY LIST (a);
CREATE TABLE fk_partitioned_fk_1 PARTITION OF fk_partitioned_fk FOR VALUES IN (NULL,500,501,502);
CREATE TABLE fk_partitioned_fk_2 PARTITION OF fk_partitioned_fk FOR VALUES IN (1500,1502);
CREATE TABLE fk_partitioned_fk_3 (a int, b int);
ALTER TABLE fk_partitioned_fk ATTACH PARTITION fk_partitioned_fk_3 FOR VALUES IN (2500,2501,2502,2503);

-- this insert fails
INSERT INTO fk_partitioned_fk (a, b) VALUES (2502, 2503);
INSERT INTO fk_partitioned_fk_3 (a, b) VALUES (2502, 2503);
-- but since the FK is MATCH SIMPLE, this one doesn't
INSERT INTO fk_partitioned_fk_3 (a, b) VALUES (2502, NULL);
-- now create the referenced row ...
INSERT INTO fk_notpartitioned_pk VALUES (2502, 2503);
--- and now the same insert work
INSERT INTO fk_partitioned_fk_3 (a, b) VALUES (2502, 2503);
-- this always works
INSERT INTO fk_partitioned_fk (a,b) VALUES (NULL, NULL);

-- ON UPDATE SET NULL
SELECT tableoid::regclass, a, b FROM fk_partitioned_fk WHERE b IS NULL ORDER BY a;
UPDATE fk_notpartitioned_pk SET a = a + 1 WHERE a = 2502;
SELECT tableoid::regclass, a, b FROM fk_partitioned_fk WHERE b IS NULL ORDER BY a;

-- ON DELETE SET NULL
INSERT INTO fk_partitioned_fk VALUES (2503, 2503);
SELECT count(*) FROM fk_partitioned_fk WHERE a IS NULL;
DELETE FROM fk_notpartitioned_pk;
SELECT count(*) FROM fk_partitioned_fk WHERE a IS NULL;

-- ON UPDATE/DELETE SET DEFAULT
INSERT INTO fk_notpartitioned_pk VALUES (2502, 2503);
INSERT INTO fk_partitioned_fk_3 (a, b) VALUES (2502, 2503);
-- this fails, because the defaults for the referencing table are not present
-- in the referenced table:
UPDATE fk_notpartitioned_pk SET a = 1500 WHERE a = 2502;
-- but inserting the row we can make it work:
INSERT INTO fk_notpartitioned_pk VALUES (2501, 142857);
UPDATE fk_notpartitioned_pk SET a = 1500 WHERE a = 2502;
SELECT * FROM fk_partitioned_fk WHERE b = 142857;

-- ON UPDATE/DELETE CASCADE
UPDATE fk_notpartitioned_pk SET a = 2502 WHERE a = 2501;
SELECT * FROM fk_partitioned_fk WHERE b = 142857;

-- Now you see it ...
SELECT * FROM fk_partitioned_fk WHERE b = 142857;
DELETE FROM fk_notpartitioned_pk WHERE b = 142857;
-- now you don't.
SELECT * FROM fk_partitioned_fk WHERE a = 142857;

-- verify that DROP works
DROP TABLE fk_partitioned_fk_2;

-- Test behavior of the constraint together with attaching and detaching
-- partitions.
CREATE TABLE fk_partitioned_fk_2 PARTITION OF fk_partitioned_fk FOR VALUES IN (1500,1502);
ALTER TABLE fk_partitioned_fk DETACH PARTITION fk_partitioned_fk_2;
BEGIN;
DROP TABLE fk_partitioned_fk;
-- constraint should still be there
\d fk_partitioned_fk_2;
ROLLBACK;
ALTER TABLE fk_partitioned_fk ATTACH PARTITION fk_partitioned_fk_2 FOR VALUES IN (1500,1502);
DROP TABLE fk_partitioned_fk_2;
CREATE TABLE fk_partitioned_fk_2 (b int, c text, a int);
ALTER TABLE fk_partitioned_fk_2 DROP COLUMN c;
ALTER TABLE fk_partitioned_fk ATTACH PARTITION fk_partitioned_fk_2 FOR VALUES IN (1500,1502);
-- should have only one constraint
\d fk_partitioned_fk_2
DROP TABLE fk_partitioned_fk_2;

CREATE TABLE fk_partitioned_fk_4 (a int, b int) PARTITION BY RANGE (b, a);
CREATE TABLE fk_partitioned_fk_4_1 PARTITION OF fk_partitioned_fk_4 FOR VALUES FROM (1,1) TO (100,100);
CREATE TABLE fk_partitioned_fk_4_2 (a int, b int);
ALTER TABLE fk_partitioned_fk_4 ATTACH PARTITION fk_partitioned_fk_4_2 FOR VALUES FROM (100,100) TO (1000,1000);
ALTER TABLE fk_partitioned_fk ATTACH PARTITION fk_partitioned_fk_4 FOR VALUES IN (3500,3502);
ALTER TABLE fk_partitioned_fk DETACH PARTITION fk_partitioned_fk_4;
ALTER TABLE fk_partitioned_fk ATTACH PARTITION fk_partitioned_fk_4 FOR VALUES IN (3500,3502);
-- should only have one constraint
\d fk_partitioned_fk_4
\d fk_partitioned_fk_4_1
-- this one has an FK with mismatched properties
\d fk_partitioned_fk_4_2

CREATE TABLE fk_partitioned_fk_5 (a int, b int) PARTITION BY RANGE (a);
CREATE TABLE fk_partitioned_fk_5_1 (a int, b int);
ALTER TABLE fk_partitioned_fk ATTACH PARTITION fk_partitioned_fk_5 FOR VALUES IN (4500);
ALTER TABLE fk_partitioned_fk_5 ATTACH PARTITION fk_partitioned_fk_5_1 FOR VALUES FROM (0) TO (10);
ALTER TABLE fk_partitioned_fk DETACH PARTITION fk_partitioned_fk_5;
ALTER TABLE fk_partitioned_fk ATTACH PARTITION fk_partitioned_fk_5 FOR VALUES IN (4500);
-- this one has two constraints, similar but not quite the one in the parent,
-- so it gets a new one
\d fk_partitioned_fk_5
-- verify that it works to reattaching a child with multiple candidate
-- constraints
ALTER TABLE fk_partitioned_fk_5 DETACH PARTITION fk_partitioned_fk_5_1;
ALTER TABLE fk_partitioned_fk_5 ATTACH PARTITION fk_partitioned_fk_5_1 FOR VALUES FROM (0) TO (10);
\d fk_partitioned_fk_5_1

-- verify that attaching a table checks that the existing data satisfies the
-- constraint
CREATE TABLE fk_partitioned_fk_2 (a int, b int) PARTITION BY RANGE (b);
CREATE TABLE fk_partitioned_fk_2_1 PARTITION OF fk_partitioned_fk_2 FOR VALUES FROM (0) TO (1000);
CREATE TABLE fk_partitioned_fk_2_2 PARTITION OF fk_partitioned_fk_2 FOR VALUES FROM (1000) TO (2000);
INSERT INTO fk_partitioned_fk_2 VALUES (1600, 601), (1600, 1601);
ALTER TABLE fk_partitioned_fk ATTACH PARTITION fk_partitioned_fk_2
  FOR VALUES IN (1600);
INSERT INTO fk_notpartitioned_pk VALUES (1600, 601), (1600, 1601);
ALTER TABLE fk_partitioned_fk ATTACH PARTITION fk_partitioned_fk_2
  FOR VALUES IN (1600);

-- leave these tables around intentionally

-- test the case when the referenced table is owned by a different user
create role regress_other_partitioned_fk_owner;
set role regress_other_partitioned_fk_owner;
create table other_partitioned_fk(a int, b int) partition by list (a);
create table other_partitioned_fk_1 partition of other_partitioned_fk
  for values in (2048);
insert into other_partitioned_fk
  select 2048, x from generate_series(1,10) x;
-- this should fail
-- add the missing keys and retry
reset role;
insert into fk_notpartitioned_pk (a, b)
  select 2048, x from generate_series(1,10) x;
set role regress_other_partitioned_fk_owner;
-- clean up
drop table other_partitioned_fk;
reset role;
revoke all on fk_notpartitioned_pk from regress_other_partitioned_fk_owner;
drop role regress_other_partitioned_fk_owner;

-- Test creating a constraint at the parent that already exists in partitions.
-- There should be no duplicated constraints, and attempts to drop the
-- constraint in partitions should raise appropriate errors.
create schema fkpart0
  create table pkey (a int primary key)
  create table fk_part (a int) partition by list (a)
  create table fk_part_1 partition of fk_par for values in (1)
  create table fk_part_23 partition of fk_part for values in (2, 3)
      partition by list (a)
  create table fk_part_23_2 partition of fk_part_23 for values in (2);

\d fkpart0.fk_part_1	\\ -- should have only one FK

\d fkpart0.fk_part_23	\\ -- should have only one FK
\d fkpart0.fk_part_23_2	\\ -- should have only one FK

create table fkpart0.fk_part_4 partition of fkpart0.fk_part for values in (4);
\d fkpart0.fk_part_4

create table fkpart0.fk_part_56 partition of fkpart0.fk_part
    for values in (5,6) partition by list (a);
create table fkpart0.fk_part_56_5 partition of fkpart0.fk_part_56
    for values in (5);
\d fkpart0.fk_part_56

-- verify that attaching and detaching partitions maintains the right set of
-- triggers
create schema fkpart1
  create table pkey (a int primary key)
  create table fk_part (a int) partition by list (a)
  create table fk_part_1 partition of fk_part for values in (1) partition by list (a)
  create table fk_part_1_1 partition of fk_part_1 for values in (1);
insert into fkpart1.fk_part values (1);		-- should fail
insert into fkpart1.pkey values (1);
insert into fkpart1.fk_part values (1);
delete from fkpart1.pkey where a = 1;		-- should fail
alter table fkpart1.fk_part detach partition fkpart1.fk_part_1;
create table fkpart1.fk_part_1_2 partition of fkpart1.fk_part_1 for values in (2);
insert into fkpart1.fk_part_1 values (2);	-- should fail
delete from fkpart1.pkey where a = 1;

-- verify that attaching and detaching partitions manipulates the inheritance
-- properties of their FK constraints correctly
create schema fkpart2
  create table pkey (a int primary key)
  create table fk_part (a int) partition by list (a)
  create table fk_part_1 partition of fkpart2.fk_part for values in (1) partition by list (a)
  create table fk_part_1_1 (a int);
alter table fkpart2.fk_part_1 attach partition fkpart2.fk_part_1_1 for values in (1);
alter table fkpart2.fk_part detach partition fkpart2.fk_part_1;

-- ensure we check partitions are "not used" when dropping constraints
CREATE SCHEMA fkpart8
  CREATE TABLE tbl1(f1 int PRIMARY KEY)
  CREATE TABLE tbl2(f1 int) PARTITION BY RANGE(f1)
  CREATE TABLE tbl2_p1 PARTITION OF tbl2 FOR VALUES FROM (minvalue) TO (maxvalue);
INSERT INTO fkpart8.tbl1 VALUES(1);
BEGIN;
INSERT INTO fkpart8.tbl2 VALUES(1);
COMMIT;

\set VERBOSITY terse	\\ -- suppress cascade details
drop schema fkpart0, fkpart1, fkpart2, fkpart8 cascade;
\set VERBOSITY default
