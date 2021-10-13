import os
import sys
import tarfile
import glob
import time
import shutil
import json
import subprocess
import mysql.connector
from distutils.util import strtobool
import configparser


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
    gtidset = None
    start_gtid = None
    start_relay_log_name = None
    start_relay_log_pos = None
    mysqlbinlog_util_abspath = None
    stop_time = None

    @classmethod
    def init_mysql_cnx(self):
        try:
            # initialize the mysql connection
            self.mysqlcnx = mysql.connector.connect(
                    option_files=self.etcfile, 
                    user=self.mysqluser, 
                    password=self.mysqlpwd, 
                    auth_plugin='mysql_native_password'
                    )
            if self.mysqlcnx.is_connected() is not True:
                raise mysql.connector.Error 

            # initialize the cursor with dictionary enabled
            self.cursor = self.mysqlcnx.cursor(dictionary=True)

        except mysql.connector.Error as err:
            print ("MySQL connect failed: {}\n".format(err))
            raise Exception(err)
        else:
            print ("MySQL connect successfully!\n")
            return True

    @classmethod
    def parse_relaypath_from_etc(self):
        try:
            config_file_parser = configparser.RawConfigParser(allow_no_value=True)
            config_file_parser.read(self.etcfile)
            self.relayLogPath = os.path.join(
                    os.path.dirname(config_file_parser.get("mysqld","relay-log")),"")
        except Exception as e:
            raise Exception(e)

    @classmethod
    def pick_bounderay_from_gtid_set(self):
        try:
            #parse the gtid str from the given gtid info file
            fd = open(self.gtidinfo,'r')
            info = fd.readlines()
            for line in info:
                self.gtidset = line.split()[2] 
                break;

            # 2209fde0-27fd-11ec-a801-7c8ae18d3c61:1,c7cbb8de-2706-11ec-9057-7c8ae18d3c61:1-12483
            sets = self.gtidset.split(",")
            sid = None
            gid = None
            for set_l in sets:
                sid = set_l.split(":")[0]
                gid_range = set_l.split(":")[1]
                if len(gid_range.split("-")) < 2:
                    continue;
                gid = gid_range.split("-")[1]
            gid = int(gid)+1;
            
            self.start_gtid = "%s:%d" % (sid,gid)
            print ("start gtid is '%s'" % self.start_gtid);
        except Exception as e:
            raise Exception(e)

    @classmethod
    def truncate_file_by_stoptime(self,index_file_name):
        if self.stop_time is None:
            return
        try:
            util_name=self.mysqlbinlog_util_abspath
            input_args1="--binlog-index-file=%s" % index_file_name
            input_args2="--stop-datetime=%s" % self.stop_time;
            input_args3="--truncate-file-by-stoptime"
            result=subprocess.check_output(\
                    [util_name, input_args1, input_args2, input_args3],\
                    shell=False)
        except subprocess.CalledProcessError as err:
            result = err.output
            print (result)


    @classmethod
    def get_filepos_by_start_gtid(self,index_file_name):
        try:
            util_name=self.mysqlbinlog_util_abspath
            input_args1="--binlog-index-file=%s" % index_file_name
            input_args2="--gtid-to-filepos=%s" % self.start_gtid
            result=subprocess.check_output([util_name, input_args1, input_args2],\
                    shell=False)
            result_dict = json.loads(result);
            self.start_relay_log_name = result_dict['filename'];
            self.start_relay_log_pos = result_dict['pos'];
        except subprocess.CalledProcessError as e:
            # can't find the specified gtid in given binlog.
            # just assign the first binlog name and pos to the
            # start_* info variables.
            self.start_relay_log_pos = "4";
            fd = open(index_file_name,"r");
            filenames = fd.readlines();
            for filename in filenames:
                self.start_relay_log_name = filename.strip();
                # just assign the first file
                break;

def sort_by_value(str_array):
    dic_by_value = {}
    for item in str_array:
        dic_by_value[int(item)] = item
    keys = dic_by_value.keys()
    keys = sorted(keys)
    return [dic_by_value[key] for key in keys]


def extract_tar(file_path, target_path):
    try:
        tar = tarfile.open(file_path, "r:gz")
        file_names = tar.getnames()
        for file_name in file_names:
            tar.extract(file_name, target_path)
        tar.close()
    except Exception as e:
        raise Exception(e)


def transfer_backup(backuppath, relaypath):
    
    backup_file = AnonymousArgs.backup_file_name;
    os.system("mkdir -p %s" % relaypath)
    shutil.copy(backuppath+backup_file,relaypath)
    # TODO
    pass


def rename_binlog_backup_to_relay(relay_log_path):
    channel_name = AnonymousArgs.channel_name
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
        dst_file_prefix = "./logfiles/relay-" + channel_name + "." 

        relay_index_file_name = "./logfiles/relay-%s.index" % channel_name
        file_hd = open(relay_index_file_name, "w")

        for index in binlog_indexs:
            os.rename(src_file_prefix + index, dst_file_prefix + index)
            file_hd.write(AnonymousArgs.relayLogPath + "relay-" + channel_name + "." + index + "\n")
        file_hd.close()

        # TODO
        # all the processed relay log and index file is in ./logfiles dirctory
        cmd = "mv %s/logfiles/* %s/" % (AnonymousArgs.relayLogPath,AnonymousArgs.relayLogPath)
        print (cmd)
        os.system(cmd)

        # Here to identify the file and pos info to feed the change
        # master statment to generate the virtual slave channel to 
        # apply the relay(backup-binlog) to the new server.
        index_file_name = "%s/relay-%s.index" % (AnonymousArgs.relayLogPath,channel_name)
        relay_index_file_name = os.path.abspath(index_file_name)
        AnonymousArgs.get_filepos_by_start_gtid(index_file_name)
        AnonymousArgs.truncate_file_by_stoptime(index_file_name)


    except Exception as e:
        raise Exception(e)


def prepare_binlog_from_backup_path():
    try:
        # localize the variable from global argument container
        binlog_backup_path = AnonymousArgs.binlog_backup_path
        relay_log_path = AnonymousArgs.relayLogPath

        # move backup.tgz to the relay path
        transfer_backup(binlog_backup_path, relay_log_path)

        # do rename staff
        rename_binlog_backup_to_relay(relay_log_path)
    except Exception as e:
        raise Exception(e)


def generate_fake_replica_channel():
    try:
        # localize the variable from global argument container
        channel_name = AnonymousArgs.channel_name
        mysql_cnx = AnonymousArgs.mysqlcnx
        start_relay_log_name = AnonymousArgs.start_relay_log_name
        start_relay_log_pos = AnonymousArgs.start_relay_log_pos

        # initialize the sql statement
        do_change_master = \
                "change master to " +\
                "master_host='2.3.4.158'," +\
                "master_port=7890, " +\
                "master_user='repl'," +\
                "master_password='repl'," +\
                "relay_log_file='%s', relay_log_pos=%s for channel '%s'" \
                % (start_relay_log_name,start_relay_log_pos,channel_name)
        print (do_change_master)


        try:
            cursor = mysql_cnx.cursor()
            # execute the change master statement
            cursor.execute(do_change_master)

        except mysql.connector.Error as err:
            print ("MySQL operation failed: {}\n".format(err))
            raise Exception(err)
        else:
            print ("change master successfully!\n")
            return True

    except Exception as e:
        raise Exception(e) 

def start_slave_sql_thread():
    try:
        # localize the variable from global argument container
        channel_name = AnonymousArgs.channel_name
        mysql_cnx = AnonymousArgs.mysqlcnx

        # initialize the sql statement
        # TODO
        # Specify the start point from the xtrabackup metadata point
        do_start_thread = "start slave sql_thread for channel '%s'" % channel_name

        try:
            # execute the change master statement
            cursor = mysql_cnx.cursor()
            cursor.execute(do_start_thread)

        except mysql.connector.Error as err:
            print ("MySQL operation failed: {}\n".format(err))
            raise Exception(err)
        else:
            print ("Do start sql_thread finish!\n")
            return True

    except Exception as e:
        raise Exception(e) 

def check_sql_thread_state():

    # localize the variable from global argument container
    channel_name = AnonymousArgs.channel_name
    cursor = AnonymousArgs.cursor

    # initialize the SQL statement
    show_slave_status_sql = "show slave status for channel '%s' " % channel_name 

    try:
        # execute the show SQL
        cursor.execute(show_slave_status_sql)
        result = cursor.fetchall()
        for rows in result:
            Slave_SQL_Running = rows['Slave_SQL_Running']
            Slave_SQL_Running_State = rows['Slave_SQL_Running_State']

            if Slave_SQL_Running == 'No':
                if rows['Last_SQL_Errno'] == 0:
                    errinfo = "Slave_SQL is not running, but Last_SQL_Errno is 0, " +\
                            "maybe the sql_thread is failed, try restart.\n"
                else:
                    errinfo = "Slave_SQL is not running, Last_SQL_Errno is %s, Last_SQL_Error is %s"\
                            % (rows['Last_SQL_Errno'],rows['Last_SQL_Error'])
                return False, errinfo 

            Slave_SQL_Running_State = rows['Slave_SQL_Running_State']

            if Slave_SQL_Running_State != "Slave has read all relay log; waiting for more updates":
                print ("Fast_apply_binlog Not finished yet, current Retrieved_Gtid_Set is %s, Executed_Gtid_Set is %s" \
                        % (rows['Retrieved_Gtid_Set'],rows['Executed_Gtid_Set']))
                time.sleep(1)
                return False, None
            else:
                print ("Fast_apply_binlog finished successfully\n")
                return True, None
    except mysql.connector.Error as err:
        return False, mysql.connector.Error(err)
    except Exception as err:
        return Exception(err)
        

def sync_confirm_relay_apply():
    try:
        retval = False
        while retval == False:
            retval,errinfo = check_sql_thread_state()
            if errinfo != None:
                print (errinfo)
                return False
    except Exception as e:
        raise Exception(e)
    else:
        return True

def do_finish_ops():
    # localize the variable from global argument container
    channel_name = AnonymousArgs.channel_name
    cursor = AnonymousArgs.cursor

    # initialize the SQL statement
    stop_slave_sql = "stop slave for channel '%s' " % channel_name 

    try:
        # execute the show SQL
        cursor.execute(stop_slave_sql)
    except mysql.connector.Error as err:
        return False, mysql.connector.Error(err)
    except Exception as err:
        return Exception(err)
        


def start_fast_apply():

    # 1.Prepare the binlog from backup , rename the binlog to relay
    prepare_binlog_from_backup_path()

    # 2.Generate the fake slave channel
    # TODO
    generate_fake_replica_channel()

    # 3.start slave sql_thread
    start_slave_sql_thread()

    # 4.confirm whether the apply finished
    retval = sync_confirm_relay_apply()

    # 5.clean the replica info.
    do_finish_ops()

    # return as the unix-like error number style
    if retval:
        sys.exit(0);

    sys.exit(1)



def print_usage():
    print ("Usage: apply_binlog_fast.py binlogBackupPath=/path/to/binlog/backup/ "\
            +"etcfile=mysql-config-file gtidinfo=/gtid/info/file/path"\
            +"stoptime=datetime_str")


if __name__ == "__main__":

    args = dict([arg.split("=") for arg in sys.argv[1:]])

    if not args.__contains__("binlogBackupPath") \
            or not args.__contains__("etcfile") \
            or not args.__contains__("gtidinfo"):
        print_usage()
        raise RuntimeError("see help info.")

    binlog_backup_path = args["binlogBackupPath"]
    etcfile = args["etcfile"]
    gtidinfo = args["gtidinfo"]

    if not os.path.exists(binlog_backup_path):
        raise ValueError(
                "Binlog backup path {} doesn't exist!".format(binlog_backup_path)
                )
        if not os.path.exists(etcfile):
            raise ValueError("DB config file {} doesn't exist!".format(etcfile))

    # init the AnonymousArgs for global use
    if args.__contains__("stoptime"):
        stop_time = args["stoptime"]
        AnonymousArgs.stop_time = stop_time
    AnonymousArgs.binlog_backup_path = os.path.join(os.path.abspath(binlog_backup_path),"")
    AnonymousArgs.etcfile = os.path.abspath(etcfile)
    AnonymousArgs.gtidinfo = os.path.abspath(gtidinfo)
    AnonymousArgs.mysqlbinlog_util_abspath = os.path.abspath("./mysqlbinlog")
    AnonymousArgs.parse_relaypath_from_etc()
    AnonymousArgs.pick_bounderay_from_gtid_set();
    AnonymousArgs.init_mysql_cnx()
    

    # entry of the fast apply binlog.
    start_fast_apply()
