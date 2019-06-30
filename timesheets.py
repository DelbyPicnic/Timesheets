#!/usr/bin/python

from datetime import date, datetime, timedelta
from tabulate import tabulate
import sqlite3 as sql
import string
import time

dbh = sql.connect('var/timesheet.db')
cursor = dbh.cursor()

max_shift = 10 # hours

# convert sql datetime string to datetime object
def to_dt(dt_in):
    return datetime.strptime(dt_in, '%Y-%m-%d %H:%M:%S')

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
    except:
        print ("Couldn't parse date or time input")
        return None

# display functions
# display a list of jobs
def display_job_list():
    # define tabulate list
    tb_header = ["ID", "Name", "Created", "Client Name", "Client Email"]
    tb_content = []
    # get jobs from database
    cursor.execute("SELECT * FROM tasksheet")
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
        # calculate shift duration
        dur = get_shift_duration(to_dt(row[2]), to_dt(row[3]))
        tb_content.append([str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(dur)])

    print (tabulate(tb_content, tb_header) + "\n")

# display all info for specific job
def display_job(tsk_name):
    try:
        # define tabulate list
        tb_header = ["ID", "Name", "Created On", "Client Name", "Business", "Email", "Rate"]
        tb_content = []
        # get job data
        cursor.execute("SELECT * FROM tasksheet WHERE task_name = ?", (tsk_name,)), 
        row = cursor.fetchone()

        for i, itm_value in enumerate (tb_header):
            tb_content.append([tb_header[i], row[i]])

        print (tabulate(tb_content) + "\n")
    except:
        print ("Couldn't find job named: " + tsk_name)

# dev functions
# clock in as yesterday's date
def clock_in_yd(tsk_name):
    cursor.execute("INSERT INTO timesheet(task_name, time_in) VALUES (?, (SELECT datetime('now','-1 day','localtime')) )", (tsk_name,))
    dbh.commit()

# reload the schema over the database file
def hard_reset():
    with open('var/schema.sql') as sch:
        cursor.executescript(sch.read())

# table i/o functions
# create a new timesheet task (job)
def new_task(tsk_name, c_name, c_business, c_email, rate):
    try:
        sql_add_task = ("INSERT INTO tasksheet (task_name, client_name, client_business, client_email, rate) VALUES (?, ?, ?, ?, ?)")
        cursor.execute(sql_add_task, (tsk_name, c_name, c_business, c_email, rate))
        dbh.commit()

    except (sql.IntegrityError):
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
                strs_end = s_end.strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("UPDATE timesheet SET time_out = ?, msg = ? WHERE time_id = ?", (strs_end, msg, row[0]))
                dbh.commit()

                print ("Clocked out of " + row[1] + " at: " + strs_end + "\nShift Duration: " + str(s_dur) + " Hours")  
                
        else:
            print("You did not clock in!")    
    else:
        print("Timesheet is empty!")

# manually enter timesheet data
def add_shift():
    return None

# edit timesheet entry
def edit_shift():
    return None

# edit tasksheet entry
def edit_job():
    return None

hard_reset()
new_task("test", "jon", "dow.inc", "jon@dow.inc", 14.00)

clock_in('test')
clock_out("done")

display_job_list()
display_timesheet("test")
display_job("test")



dbh.close()