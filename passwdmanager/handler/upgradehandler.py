# PasswdManager -- Password management tool
# Copyright (C) 2009 -- 2013 Kai Yuan <kent.yuan@gmail.com>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import shutil
import datetime
import sqlite3 as sqlite
import passwdmanager.config as config
import passwdmanager.util as util
import passwdmanager.service as service
import passwdmanager.dao as dao
import os.path

def __getConnection():
    """
    get database connection
    """
    conn = sqlite.connect(config.CONN_PATH)
    return conn

def upgrade():
    """
    do the upgrade logic
    """
    msg  = '' #return value
    conn = __getConnection()
    #root password
    key  = config.getRootPwd()

    if __table_exists(conn, "config"):
        version = read_data_version(conn)
        if version != config.VERSION:
            update_data_version(conn)
            # do upgrade if needed, update version 
    else:
        #check if Account.secret column exits
        v10x = not __column_exists(conn, 'account','secret')
        #do upgrade here
        msg  = __upgrade_10x_110(key,conn,v10x)

        
        #create config table
        sql = """
            CREATE TABLE CONFIG ( 
            name TEXT(200) NOT NULL, 
            value TEXT(500) NOT NULL 
            ); """
        ins_sql = """insert into config(name,value) values(?,?) ;"""

        cur = conn.cursor()
        cur.execute(sql)
        cur.execute(ins_sql,('version',config.VERSION,))
        conn.commit()
        cur.close()
    return msg



def __upgrade_10x_110(key, conn, v10x):
    """
    upgrade from version 1.0.x or 1.1.0
    return message, used for gui dialog
    """

    #do backup first
    ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    filename = ts + '_data_b4_Upgrade.backup'
    util.backupDB_with_fn(filename)
    

    cur = conn.cursor()
    # add ACCESS_CNT column
    sql_add_cnt = """ ALTER TABLE ACCOUNT ADD COLUMN ACCESS_CNT INT """
    cur.execute(sql_add_cnt)

    if v10x:
        #version 1.0.x, create secret column is required
        sql_add_secret = """ ALTER TABLE ACCOUNT ADD COLUMN secret TEXT """
        cur.execute(sql_add_secret)
    sql = 'select id,  username,password, secret FROM ACCOUNT'
    upsql = 'update Account set username=?, password=?, secret=? where id=?'
    cur = conn.cursor()
    cur.execute(sql)

    cur2 =conn.cursor()
    for row in cur.fetchall():
        (id,uid,pwd,secret) = row

        newUid=util.encrypt(key ,uid) if v10x else util.reencrypt_with_pycrp26(key, uid)
        newPwd = util.reencrypt_with_pycrp26(key,pwd)
        newSecret = util.reencrypt_with_pycrp26(key,secret) if not v10x else secret
        
        cur2.execute(upsql,(newUid,newPwd,newSecret, id,))
    cur2.close()
    cur.close()
    msg = "Data file is converted from old version({0}). Backup could be found at {1}".format('1.0.x' if v10x else '1.1.0', os.path.join(config.BACKUP_DIR,filename))
    return msg



def __column_exists(conn,table_name,column_name):
    sql = "PRAGMA table_info(" + table_name + ")"
    cur = conn.cursor()
    cur.execute(sql)
    result = False
    for row in cur.fetchall():
        if row[1]==column_name:
            result = True
            break
    cur.close()
    return result


def __table_exists(conn,table_name):
    sql = "PRAGMA table_info(" + table_name + ")"
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return len(rows)>0

def read_data_version(conn):
    sql = "select value from config where name=?"
    cur = conn.cursor()
    cur.execute(sql, ('version',))
    ver = cur.fetchone()[0]
    cur.close()
    return ver

def update_data_version(conn):
    sql = "update config set value=? where name=?"
    cur = conn.cursor()
    cur.execute(sql,(config.VERSION,'version',))
    cur.close()



