#!/usr/bin/python

from datetime import date, datetime, timedelta
from tabulate import tabulate
import sqlite3 as sql
from sqlite3 import Error
import string
import time

dbh = sql.connect('var/timesheet.db')
cursor = dbh.cursor()

max_shift = 10 # hours
debug = False
dt_format = '%Y-%m-%d %H:%M:%S'
bk_dir = 'backup/'

# convert sql datetime string to datetime object
def to_dt(dt_in):
    return datetime.strptime(dt_in, dt_format)

# convert UTC to local timezone (+1 hour for UK)
def get_dt_now():
    return (datetime.utcnow() + timedelta(hours=1))

# return the difference between two datetime objects in hours
def get_shift_duration(t_in, t_out):
    # get timedelta duration
    dur = (t_out - t_in)
    # get total seconds
    dur = dur.total_seconds()
    # return duration in hours
    return dur//3600

# validate a manual clock in time
def validate_shift(t_in, t_out):
    # clock out can't be before clock in
    if (t_in > t_out):
        print ("Clock-in can't be after clock-out")
        return False
    # shift can't be longer than the maximum shift length
    if (get_shift_duration(t_in, t_out) > max_shift):
        print ("Shift exceeds the maximum length of " + str(max_shift) + " hours")
        return False
    # shift cannot partly or fully take place in the future
    if (t_in > get_dt_now() or t_out > get_dt_now()):
        print ("Shifts can't start or end in the future")
        return False

    return True

# get manual date and time from prompt
def prompt_for_time():
    try:
        # get manual date from prompt and convert to dt object
        date_in = input("Enter Date: (yyyy-mm-dd) > ")
        m_date = datetime.strptime(date_in, '%Y-%m-%d')

        # get manual time from prompt and convert to dt object
        time_in = input("Enter Time: (hh:mm:ss) > ")
        m_time = datetime.strptime(time_in, '%H:%M:%S').time()
        
        # merge date and time into complete datetime object
        full_date = datetime.combine(m_date, m_time)
        return full_date

    except Error as err:
        print ("Couldn't parse date or time input")
        return None

# display functions
# display a list of jobs
def display_job_list():
    # define tabulate list
    tb_header = ["ID", "Name", "Created", "Client Name", "Client Email"]
    tb_content = []
    # get jobs from database
    cursor.execute("""
        SELECT tasksheet.task_id, tasksheet.task_name, tasksheet.created_on, clients.client_name, clients.client_email 
        FROM tasksheet
        JOIN clients ON tasksheet.client_id = clients.client_id
    """)
    for row in cursor:
        tb_content.append([str(row[0]), str(row[1]), str(row[2]), str(row[3])])

    print (tabulate(tb_content, tb_header) + "\n") 

def display_timesheet(tsk_name):
    # define tabulate list
    tb_header = ["ID", "Description", "Start", "End", "Duration (hrs)"]
    tb_content = []

    # get timesheet data
    cursor.execute("SELECT * FROM timesheet WHERE task_name = ?", (tsk_name,))
    for row in cursor:
        tb_content.append([str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4])])

    print (tabulate(tb_content, tb_header) + "\n")

# display all info for specific job
def display_job(tsk_name):
    try:
        # define tabulate list
        tb_header = ["ID", "Name", "Created On", "Client Name", "Business", "Email", "Rate"]
        tb_content = []
        # get job data
        cursor.execute("""
            SELECT tasksheet.task_id, tasksheet.task_name, tasksheet.created_on, clients.client_name, clients.client_business, clients.client_email, tasksheet.rate
            FROM tasksheet
            JOIN clients ON tasksheet.client_id = clients.client_id
            WHERE tasksheet.task_name = ?
        """, (tsk_name,)), 
        row = cursor.fetchone()

        for i, itm_value in enumerate (tb_header):
            tb_content.append([tb_header[i], row[i]])

        print (tabulate(tb_content) + "\n")

    except Error as err:
        print ("Couldn't display job named: " + tsk_name + ".\n" + str(err))

# table i/o functions
# init the database file with the correct tables in the schema
def init_database():
    with open('var/schema.sql') as sch:
        cursor.executescript(sch.read())

# create a new client
def new_client(c_name, c_business, c_address, c_email, c_phone):
    try:
        sql_add_client = ("INSERT INTO clients (client_name, client_business, client_address, client_email, client_phone) VALUES (?, ?, ?, ?, ?)")
        cursor.execute(sql_add_client, (c_name, c_business, c_address, c_email, c_phone))
        dbh.commit()

    except (sql.IntegrityError) as err:
        print ("Can't create new client: " + c_name + ".\n" + str(err))
        pass

# create a new timesheet task (job)
def new_task(tsk_name, c_email, rate):
    try:
        # find client id from client email
        cursor.execute("SELECT client_id FROM clients WHERE client_email = ?", (c_email,))
        row = cursor.fetchone()

        # if the client exists, save the client id with the task
        if (row is not None):
            sql_add_task = ("INSERT INTO tasksheet (task_name, client_id, rate) VALUES (?, ?, ?)")
            cursor.execute(sql_add_task, (tsk_name, row[0], rate))
            dbh.commit()
        else:
            print ("Can't find client with email: " + c_email + "\nDoes the client exist?")

    except (sql.IntegrityError) as err:
        print ("Can't create new task: " + tsk_name + "\nDoes a task with this name already exist?")
        pass   

# clock in for a specific job 
def clock_in(tsk_name):
    cursor.execute("INSERT INTO timesheet(task_name) VALUES (?)", (tsk_name,))
    dbh.commit()

# clock out of the last shift for any job
def clock_out(msg):
    cursor.execute("SELECT * FROM timesheet ORDER BY time_id DESC LIMIT 1")
    row = cursor.fetchone()
    if (row is not None):
        if (row[3] is None):
            # declare shift end time
            s_end = None
            # attempt to automatically clock out
            if (not validate_shift(to_dt(row[2]), get_dt_now())):
                # time dfference between clock in and now is longer than the max shift length
                print ("Can't automatically clock out of " + row[1] + ":" + row[2] + "\nEnter your clock-out time manually")
                s_end = prompt_for_time()

                # verify that the manual clock out time is valid
                if (s_end is None or not validate_shift(to_dt(row[2]), s_end)):
                    print ("Manual clock-out is still invalid")
                    return None
                
            else:
                # automatically clock out last shift
                s_end = get_dt_now()

            if (s_end is not None):
                # get shift duration
                s_dur = get_shift_duration(to_dt(row[2]), s_end)

                # convert shift end to string and save
                strs_end = s_end.strftime(dt_format)
                cursor.execute("UPDATE timesheet SET time_out = ?, duration = ?, msg = ? WHERE time_id = ?", (strs_end, s_dur, msg, row[0]))
                dbh.commit()

                print ("Clocked out of " + row[1] + " at: " + strs_end + "\nShift Duration: " + str(s_dur) + " Hours")  
                
        else:
            print("You did not clock in!")    
    else:
        print("Timesheet is empty!")

# manually enter timesheet data
def new_shift(tsk_name, time_in, time_out, msg):
    try:
        # validate the shift entry
        if (validate_shift(time_in, time_out)):
            # set shift message
            if (msg is None or msg == ""):
                s_msg = "no description"
            else:
                s_msg = msg

            # get shift duration
            s_dur = get_shift_duration(time_in, time_out)          
            
            s_summary = (tsk_name, time_in.strftime(dt_format), time_out.strftime(dt_format), s_dur, s_msg)

            # save shift to database
            cursor.execute("INSERT INTO timesheet (task_name, time_in, time_out, duration, msg) VALUES (?, ?, ?, ?, ?)", s_summary)
            dbh.commit()

            print ("New shift added for " + tsk_name + ".\nShift Duration: " + str(s_dur) + " Hours")
        else:
            print ("Shift details are invalid")

    except (sql.IntegrityError):
        print ("Could not find a job entry with name: " + str(tsk_name))

# delete shift
def del_shift(time_id):
    try:
        cursor.execute("DELETE FROM timesheet WHERE time_id = ?", (time_id,))
        dbh.commit()
    except Error as e:
        print ("Could not remove shift entry with id: " + str(time_id))
    
# delete the last shift entry for a given job
def del_last_shift(tsk_name):
    # find last entered shift for job
    cursor.execute("SELECT time_id FROM timesheet WHERE task_name = ? ORDER BY time_id DESC LIMIT 1", (str(tsk_name),))
    row = cursor.fetchone()

    if (row is not None):
        # delete entry with retrieved ID
        del_shift(row[0])

        print ("Deleted shift entry with ID: " + str(row[0]) + " for job: " + str(tsk_name))
    else:
        print ("Couldn't find any shift entries for job named: " + str(tsk_name))

# create a backup of the database to a new sqlite3.db file
def backup_db():
    try:
        # generate backup name
        bk_name = str(datetime.now().strftime('%Y%m%d%H%M') + '.sql')
        # open connection
        with open((bk_dir + bk_name), 'w') as f:
            for line in dbh.iterdump():
                f.write('%s\n' % line)
        

        print ("Successfully backed up timesheets to: " + bk_name)
    except Error as err:
        print ("Could not create backup: " + err)
        

init_database()
new_client("jon", "dow.inc", "123 some street, edinburgh, eh10 5aa", "jon@dow.com", "0131 555 6969")
new_task("test", "jon@dow.com", 14.00)

clock_in('test')
clock_out("done")

mytime_in = to_dt('2019-07-01 08:00:00')
mytime_out = to_dt('2019-07-01 17:00:00')

new_shift('test', mytime_in, mytime_out, 'manual test shift')
backup_db()
del_last_shift('test')

display_job_list()
display_timesheet("test")
display_job("test")



dbh.close()