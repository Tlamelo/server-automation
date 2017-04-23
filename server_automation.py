#!/usr/bin/env python3
import hjson, fcntl, shutil, signal, sys, pexpect

# Define the constant to hold the special string that will be used as
# the delimiter when splitting the arguments from the command line
import struct

import termios

DELIMITER = "<------->"

# Commands that will be used through the command line
CONNECT = 'connect'
LIST = 'list'

# Accepted commands
ACCEPTED_COMMANDS = {
    CONNECT: """
        Connects to a given server using the alias provided.
        Example ./server_automation connect saved_alias
        """,
    LIST: """
        Provides a list of aliases. An alias is how you identify 
        the server that you have configured.
        Example ./server_automation list
        """}

CONFIG_FILE = 'config_live.hjson'


def log(result, other=None):
    """Logging the results into the console"""
    if other is None:
        print(result)
    else:
        print(result, other)


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
    saved_aliases = []
    server = None

    with open(CONFIG_FILE, 'r') as file:
        config = hjson.load(file)

    # Get the username and password
    for server_item in config['servers']:
        saved_aliases.extend(server_item['aliases'])

        if server_alias in server_item['aliases']:
            found_alias = True
            server = server_item
            break

    if found_alias is False:
        log('No such alias exists. Get the available aliases using: '
            ' ./server_automation.py list')

        sys.exit(1)

    return server


def sigwinch_pass_through():
    s = struct.pack("HHHH", 0, 0, 0, 0)
    a = struct.unpack('hhhh',
                      fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, s))
    global controller
    controller.setwinsize(a[0], a[1])


def server_login(server_details, app_controller=None):
    """
    Logs into the server specified and any required servers
    """
    if 'requiredServerLogIn' in server_details:
        # Connect to the server
        app_controller = server_login(get_server_details(server_details['requiredServerLogIn']), app_controller)

    # Connect to the server
    app_controller = ssh_log_in(server_details['server'],
                                server_details['username'],
                                server_details['password'],
                                server_details['serverDisplayName'],
                                server_details['port'],
                                app_controller)

    return app_controller

if __name__ == '__main__':
    # Get the arguments passed
    args = sys.argv[1:]

    try:
        assert len(args) >= 1
    except AssertionError:
        log('Supported commands are: \n{}'.format("\n".join(
            ["{0}: {1}".format(key, value) for key, value in ACCEPTED_COMMANDS.items()])))

        sys.exit(1)

    # Save the first arg
    first_arg = args[0]

    # Check if the fist argument is a supported command
    if first_arg not in ACCEPTED_COMMANDS.keys():
        log('Supported commands are: \n{}'.format("\n".join(
            ["{0}: {1}".format(key, value) for key, value in ACCEPTED_COMMANDS.items()])))

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
        details = get_server_details(alias)

        controller = server_login(details)

        # Get the window size and update the app controller
        column, row = shutil.get_terminal_size((80, 20))
        controller.setwinsize(row, column)

        # Notify incase of a window size change
        signal.signal(signal.SIGWINCH, sigwinch_pass_through)
        controller.interact()

    elif first_arg == LIST:
        # Get the list of all aliases
        all_aliases = []

        with open(CONFIG_FILE, 'r') as f:
            data = hjson.load(f)

            try:
                assert len(args) >= 1
            except AssertionError:
                log('Config file:{config} does not exist or is empty.'
                    .format(config=CONFIG_FILE))

        for item in data['servers']:
            all_aliases.append({
                "server": item['server'],
                "aliases": item['aliases']})

        log("The list of aliases/servers are: ")
        for item in all_aliases:
            log("Aliases: {aliases} \n\t Server: {server}"
                .format(server=item['server'],
                        aliases=", ".join(item['aliases'])))

        sys.exit(0)
    else:
        log('Unimplemented command {command} {accepted_commands}'.format(
            command=first_arg,
            accepted_commands=str(ACCEPTED_COMMANDS.keys())))

        sys.exit(0)
