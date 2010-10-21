#!/usr/bin/env python

import sys, os
import subprocess, shlex
from ConfigParser import RawConfigParser
import MySQLdb

script_path = os.path.dirname(sys.argv[0])

def input_default(value_name, default_value):
    """Asks the user to input a value `value_name`, and returns
    `default_value` if the input string is empty."""
    user_string = raw_input('Please enter the %s [%s]: ' % (value_name, default_value))
    if user_string == '':
        return default_value
    return user_string

def get_program_output(args):
    """Executes the command line specified in `args` and returns the output."""
    sub = subprocess.Popen(shlex.split(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return sub.communicate()[0]


def setup():
    keys_defaults = [{'name': 'digitemp_path'  , 'default': 'digitemp'},
                     {'name': 'digitemp_tty'   , 'default': '/dev/ttyS0'},
                     {'name': 'mysql_host'     , 'default': 'localhost'},
                     {'name': 'mysql_port'     , 'default': '3306'},
                     {'name': 'mysql_user'     , 'default': ''},
                     {'name': 'mysql_password' , 'default': ''},
                     {'name': 'mysql_database' , 'default': 'temperature'}]

    config = RawConfigParser()

    for x in keys_defaults:
        section, option = x['name'].split('_')
        config.has_section(section) or config.add_section(section)
        config.set(section, option, input_default(x['name'], x['default']))

    print 'Writing config to temperature.conf'
    config.write(open(os.path.join(script_path, 'temperature.conf'), 'w'))

    print 'Writing base digitemprc'
    f = open('digitemprc', 'w')
    f.write(
'''TTY %s
READ_TIME 1000
LOG_TYPE 1
LOG_FORMAT "%%N %%R %%C"
CNT_FORMAT " "
HUM_FORMAT " "
SENSORS 0
''' % (config.get('digitemp', 'tty')))
    f.close()

    print 'Initializing digitemprc sensor list'
    digitemp_cmd_base = config.get('digitemp', 'path') + ' -q -c ' + os.path.join(script_path, 'digitemprc') + ' '
    get_program_output(digitemp_cmd_base + '-i')
    
    print 'Fetching list of sensors'
    sensors = [x.split(' ')[0] for x in get_program_output(digitemp_cmd_base + '-w').split('\n')[:-1]]

    db = MySQLdb.connect(host = config.get('mysql', 'host'),
                         port = int(config.get('mysql', 'port')),
                         user = config.get('mysql', 'user'),
                         passwd = config.get('mysql', 'password'),
                         db = config.get('mysql', 'database'))
    cursor = db.cursor()
    for sensor in sensors:
        desc = raw_input('Please enter a description for sensor %s: ' % sensor)
        cursor.execute("INSERT INTO `sensors` (`serial`, `description`) VALUES ('%s', '%s')" % (sensor, desc))
    db.commit()
    del cursor, db

    print "Setup complete"

def update():
    """Updates the MySQL database with new temperature data from
    the sensors."""
    config = RawConfigParser()
    config.read(os.path.join(script_path, 'temperature.conf'))

    db = MySQLdb.connect(host = config.get('mysql', 'host'),
                         port = int(config.get('mysql', 'port')),
                         user = config.get('mysql', 'user'),
                         passwd = config.get('mysql', 'password'),
                         db = config.get('mysql', 'database'))
    cursor = db.cursor()

    sensor_data = get_program_output(config.get('digitemp', 'path') +
                                     ' -q -a -c ' +
                                     os.path.join(script_path, 'digitemprc')).split('\n')[:-1]

    for line in sensor_data:
        timestamp, sensor, temperature = line.split(' ')
        cursor.execute("INSERT INTO `data` (`timestamp`, `sensor`, `temperature`) "
                       "VALUES ('%s', (SELECT `id` FROM `sensors` WHERE serial='%s'), '%s')"
                       % (timestamp, sensor, temperature))
        db.commit()
    del cursor, db

def show_help():
    print "Usage: %s <setup | update>" % sys.argv[0]

if __name__ == '__main__':
    modes = {'update': update, 'setup': setup}
    if len(sys.argv) <= 1 or sys.argv[1] not in modes:
        show_help()
    else:
        modes[sys.argv[1]]()
