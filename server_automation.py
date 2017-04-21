#!/usr/bin/env python
import json
import pexpect
import sys

# Define the constant to hold the special string that will be used as
# the delimiter when splitting the arguments from the command line
DELIMITER = "<------->"

# Commands that will be used through the command line
CONNECT = 'connect'
CREATE = 'create'

# Accepted commands
ACCEPTED_COMMANDS = (CONNECT, CREATE)


def log(result, other=""):
    """Logging the results into the console"""
    print(result + str(other))


def expected(child, expected_string):
    """Function to handle the expected output"""

    # Check if the string passed is the expected string
    try:
        child.expect(expected_string, timeout=10)
    except pexpect.EOF:
        log("EOF, Failed to match expected result: ", expected_string)
        log("\t----> After: ", child.after)
        sys.exit(1)
    except pexpect.TIMEOUT:
        log("TIMEOUT, Failed to match expected result: ", expected_string)
        log("\t----> After: ", child.after)
        sys.exit(1)
    except:
        log("Failed to match expected result: ", expected_string)
        log("\t----> After: ", child.after)
        sys.exit(1)


def ssh_log_in(server_ip, username, password, server_display_name, port=22, app_controller=None):
    """
    This function logs in into a server with the arguments passed
    """

    # Spawn a ssh session
    command = 'ssh %s@%s -p%d' % (username, server_ip, port)

    # Log
    log("----> Logging in with the command: %s" % command)

    # Run the command
    if app_controller is None:
        app_controller = pexpect.spawn(command)
    else:
        app_controller.sendline(command)

    # Expect the password
    expected(app_controller, 'assword:')

    # Insert the password
    app_controller.sendline(password)

    # Expect the username and server display name
    expected(app_controller, '%s@%s' % (username, server_display_name))

    log("<---- Successfully logged into the server: " + server_ip + "\n")

    return app_controller


# Function to run command on the server
def run_command(app_controller, command, expected_string=".*"):
    log("\nRunning the command %s" % command)

    app_controller.sendline(command)

    # Check if the string passed is the expected string
    expected(app_controller, expected_string)

    return app_controller


def get_server_details(server_alias):
    """
    Get the server details from the config file using the alias provided. The server details are username,
    password, server, port, serverDisplayName, requiredServerLogIn
    :param server_alias: String used to identify a server in the config file
    :return: server details
    """
    found_alias = False
    aliases = []
    server = None

    with open('config.json', 'r') as file:
        config = json.load(file)

    # Get the username and password
    for server in config['servers']:
        aliases.extend(server['aliases'])

        if server_alias in server['aliases']:
            found_alias = True
            server = server
            break

    if found_alias is False:
        log("No such alias exists. Current aliases are: ", str(aliases))
        sys.exit(1)

    return server


def server_login(server_details, app_controller=None):
    """
    Logs into the server specified and any required servers
    :param server_details: 
    :param app_controller: 
    :return: 
    """
    if 'requiredServerLogIn' in server_details:
        # Connect to the server
        app_controller = server_login(get_server_details(server_details['requiredServerLogIn']), app_controller)

    # Connect to the server
    app_controller = ssh_log_in(server_details['server'], server_details['username'],
                                server_details['password'], server_details['serverDisplayName'],
                                server_details['port'], app_controller)

    return app_controller

if __name__ == '__main__':
    # Get the arguments passed
    args = sys.argv[1:]

    try:
        assert len(args) >= 1
    except AssertionError:
        log('Supported commands are {}'.format(str(ACCEPTED_COMMANDS)))
        sys.exit(1)

    # Save the first arg
    first_arg = args[0]

    # Check if the fist argument is a supported command
    if first_arg not in ACCEPTED_COMMANDS:
        log('Supported commands are {}'.format(str(ACCEPTED_COMMANDS)))
        sys.exit(1)

    # Handle each command
    if first_arg == CONNECT:
        # Check if the alias was passed as the second argument
        try:
            assert type(args[1]) is str
        except:
            log("No alias was passed, please pass an alias. "
                "Format \"./server_automation.py connect alias_name\"")
            sys.exit(1)

        alias = args[1]
        server_details = get_server_details(alias)

        controller = server_login(server_details)

        controller.interact()

    elif first_arg == CREATE:
        pass
    else:
        log('Unimplemented command'.format(first_arg, str(ACCEPTED_COMMANDS)))
        sys.exit(1)
