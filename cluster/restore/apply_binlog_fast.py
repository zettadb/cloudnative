#!/usr/bin/python2.7
import os
import sys
import re
import time
import random
import fcntl
import struct
import socket
import subprocess
import json
import shlex
import tarfile
import glob
import mysql.connector
from distutils.util import strtobool


# Below is the real story
class AnonymousArgs:
    backup_file_name = "backup.tar.gz"
    binlog_backup_path = None
    etcfile = None
    relayLogPath = None
    mysqluser = "root"
    mysqlpwd = "root"
    mysqlcnx = None
    cursor = None
    channel_name = "fast_apply_channel"

    @classmethod
    def init_mysql_cnx(self):
        try:
            # initialize the mysql connection
            self.mysqlcnx = mysql.connector.connect(
                    option_files=self.etcfile, user=self.mysqluser, password=self.mysqlpwd, auth_plugin='mysql_native_password'
                    )
            if self.mysqlcnx.is_connected() is not True:
                raise mysql.connector.Error 

            # initialize the cursor with dictionary enabled
            self.cursor = self.mysqlcnx.cursor(dictionary=True)

        except mysql.connector.Error as err:
            print "MySQL connect failed: {}\n".format(err)
            raise Exception, err
        else:
            print "MySQL connect successfully!\n"
            return True

    def parse_relaypath_from_etc():
        # TODO
        pass


def sort_by_value(str_array):
    dic_by_value = {}
    for item in str_array:
        dic_by_value[int(item)] = item
    keys = dic_by_value.keys()
    keys.sort()
    return [dic_by_value[key] for key in keys]


def extract_tar(file_path, target_path):
    try:
        tar = tarfile.open(file_path, "r:gz")
        file_names = tar.getnames()
        for file_name in file_names:
            tar.extract(file_name, target_path)
        tar.close()
    except Exception, e:
        raise Exception, e


def transfer_backup(backuppath, relaypath):
    # TODO

    pass


def rename_binlog_backup_to_relay(relay_log_path):
    try:
        os.chdir(relay_log_path)
        # Attention : cwd have already changed to relay_log_path

        extract_tar(AnonymousArgs.backup_file_name, "./")
        ls_result = glob.glob("./logfiles/binlog.*")

        binlog_indexs = []
        for names in ls_result:
            # trim the path to get the pure binlog index
            index_str = os.path.basename(names).split(".")[1:][0]
            binlog_indexs.append(index_str)

        # sort the array
        binlog_indexs = sort_by_value(binlog_indexs)

        src_file_prefix = "./logfiles/binlog."
        dst_file_prefix = "./logfiles/relay."

        relay_index_file_name = "./logfiles/relay.index"
        file_hd = open(relay_index_file_name, "w")

        for index in binlog_indexs:
            os.rename(src_file_prefix + index, dst_file_prefix + index)
            file_hd.write(AnonymousArgs.relayLogPath + "/relay." + index + "\n")
        file_hd.close()

        # TODO
        # all the processed relay log and index file is in ./logfiles dirctory

    except Exception, e:
        raise Exception, e


def prepare_binlog_from_backup_path():
    try:
        # localize the variable from global argument container
        binlog_backup_path = AnonymousArgs.binlog_backup_path
        relay_log_path = AnonymousArgs.relayLogPath

        # move backup.tgz to the relay path
        transfer_backup(binlog_backup_path, relaylogpath)

        # do rename staff
        rename_binlog_backup_to_relay(relay_log_path)
    except Exception, e:
        raise Exception, e


def generate_fake_replica_channel(start_relay_file_name, start_relay_file_pos):
    try:
        # localize the variable from global argument container
        channel_name = AnonymousArgs.channel_name
        mysql_cnx = AnonymousArgs.mysqlcnx

        # initialize the sql statement
        do_change_master = \
                "change master to \
                master_host='2.3.4.255',\
                master_port=7890, \
                master_user='repl',\
                master_password='repl',\
                relay_log_file='%s',\
                relay_log_pos=%s \
                for channel '%s'" \
                % (start_relay_file_name,start_relay_file_pos,channel_name)

        try:
            cursor = mysql_cnx.cursor()
            # execute the change master statement
            cursor.execute(do_change_master)

        except mysql.connector.Error as err:
            print "MySQL operation failed: {}\n".format(err)
            raise Exception, err
        else:
            print "change master successfully!\n"
            return True

    except Exception, e:
        raise Exception, e 

def start_slave_sql_thread():
    try:
        # localize the variable from global argument container
        channel_name = AnonymousArgs.channel_name
        mysql_cnx = AnonymousArgs.mysqlcnx

        # initialize the sql statement
        # TODO
        # Specify the start point from the xtrabackup metadata point
        do_start_thread = "start slave sql_thread for %s" % channel_name

        try:
            # execute the change master statement
            cursor = mysql_cnx.cursor()
            cursor.execute(do_start_thread)

        except mysql.connector.Error as err:
            print "MySQL operation failed: {}\n".format(err)
            raise Exception, err
        else:
            print "Do start sql_thread finish!\n"
            return True

    except Exception, e:
        raise Exception, e 

def check_sql_thread_state():

    # localize the variable from global argument container
    channel_name = AnonymousArgs.channel_name
    cursor = AnonymousArgs.cursor

    # initialize the SQL statement
    show_slave_status_sql = "show slave status for channel '%s' " % channel_name 

    try:
        # execute the show SQL
        cursor.execute(show_slave_status_sql)
        for rows in cursor:
            Slave_SQL_Running = rows['Slave_SQL_Running']
            Slave_SQL_Running_State = rows['Slave_SQL_Running_State']

            if Slave_SQL_Running == 'No':
                if rows['Last_SQL_Errno'] == 0:
                    errinfo = "Slave_SQL is not running, but Last_SQL_Errno is 0, \
                            maybe the sql_thread is failed, try restart.\n"
                else:
                    errinfo = "Slave_SQL is not running, Last_SQL_Errno is %s, Last_SQL_Error is %s"\
                            % (rows['Last_SQL_Errno'],rows['Last_SQL_Error'])
                return False, errinfo 

            Slave_SQL_Running_State = rows['Slave_SQL_Running_State']

            if Slave_SQL_Running_State != "Slave has read all relay log; waiting for more updates":
                print "fast apply binlog is not finished, current Relay_Log_File is %s, \
                        Relay_Log_Pos is %s" % (rows['Relay_Log_File'],rows['Relay_Log_Pos'])
                time.sleep(1)
                return False, None
            else:
                print "fast apply binlog finished successfully\n"
                return True, None
    except mysql.connector.Error as err:
        raise mysql.connector.Error, err

def sync_confirm_relay_apply():
    try:
        retval = False
        while retval == False:
            retval,errinfo = check_sql_thread_state()
            if errinfo != None:
                print errinfo
                return False
    except Exception, e:
        raise Exception, e
    else:
        return True

def start_fast_apply():
    try:
        # 1.Prepare the binlog from backup , rename the binlog to relay
        prepare_binlog_from_backup_path()

        # 2.Generate the fake slave channel
        generate_fake_replica_channel()

        # 3.start slave sql_thread
        start_slave_sql_thread()

        # 4.confirm whether the apply finished
        sync_confirm_relay_apply()

        # 5.clean the replica info.
        do_finish_ops()

    except Exception, e:
        raise Exception, e


def print_usage():
    print "Usage: fast_apply_binlog.py binlogBackupPath=/path/to/binlog/backup/ etcfile=mysql-config-file "


if __name__ == "__main__":

    args = dict([arg.split("=") for arg in sys.argv[1:]])

    if not args.has_key("binlogBackupPath") or not args.has_key("etcfile"):
        print_usage()
        raise RuntimeError("Must specify binlogBackupPath or etcfile arguments.")

    binlog_backup_path = args["binlogBackupPath"]
    etcfile = args["etcfile"]

    if not os.path.exists(binlog_backup_path):
        raise ValueError(
                "Binlog backup path {} doesn't exist!".format(binlog_backup_path)
                )
        if not os.path.exists(etcfile):
            raise ValueError("DB config file {} doesn't exist!".format(etcfile))

    # init the AnonymousArgs for global use
    AnonymousArgs.binlog_backup_path = binlog_backup_path
    AnonymousArgs.etcfile = etcfile
    AnonymousArgs.parse_relaypath_from_etc()

    # entry of the fast apply binlog.
    start_fast_apply()
