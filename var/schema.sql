DROP TABLE tasksheet;
DROP TABLE timesheet;

CREATE TABLE IF NOT EXISTS tasksheet (
    task_id integer PRIMARY KEY AUTOINCREMENT,
    task_name varchar UNIQUE,
    created_on datetime DEFAULT (datetime('now','localtime')),
    client_name varchar,
    client_business varchar,
    client_email varchar,
    rate float
);

CREATE TABLE IF NOT EXISTS timesheet  (
    time_id integer PRIMARY KEY AUTOINCREMENT,
    task_name varchar(200) NOT NULL,
    time_in datetime DEFAULT (datetime('now','localtime')),
    time_out datetime,
    msg text,
    foreign key (task_name) references tasksheet(task_name)
);