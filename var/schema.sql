DROP TABLE IF EXISTS tasksheet;
DROP TABLE IF EXISTS timesheet;
DROP TABLE IF EXISTS clients;
DROP TABLE IF EXISTS invoices;
DROP TABLE IF EXISTS settings;

CREATE TABLE settings (
    s_section varchar DEFAULT 'app',
    s_name varchar NOT NULL,
    s_value varchar NOT NULL,
    s_type tinyint NOT NULL,
    primary key (s_section, s_name)
);

CREATE TABLE clients (
    client_id integer PRIMARY KEY AUTOINCREMENT,
    client_name varchar NOT NULL,
    client_business varchar NOT NULL,
    client_address varchar NOT NULL,
    client_email varchar UNIQUE,
    client_phone varchar
);

CREATE TABLE invoices (
    inv_id integer PRIMARY KEY AUTOINCREMENT,
    inv_created_on datetime DEFAULT (datetime('now','localtime')),
    inv_date_start datetime NOT NULL,
    inv_date_end datetime NOT NULL,
    task_name varchar UNIQUE,
    inv_tax_rate float NOT NULL,
    inv_discount float DEFAULT 0.00,
    inv_total float DEFAULT 0.00,
    inv_file varchar NOT NULL,
    foreign key (task_name) references tasksheet(task_name)
);

CREATE TABLE tasksheet (
    task_id integer PRIMARY KEY AUTOINCREMENT,
    task_name varchar UNIQUE,
    created_on datetime DEFAULT (datetime('now','localtime')),
    client_id integer NOT NULL,
    rate float,
    foreign key (client_id) references clients(client_id)
);

CREATE TABLE timesheet  (
    time_id integer PRIMARY KEY AUTOINCREMENT,
    task_name varchar(200) NOT NULL,
    time_in datetime DEFAULT (datetime('now','localtime')),
    time_out datetime,
    duration integer,
    msg text,
    foreign key (task_name) references tasksheet(task_name)
);