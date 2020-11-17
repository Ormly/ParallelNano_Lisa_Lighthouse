#
# TPRO 2020
#
"""
Shutdown adapter script
"""
import sys
import subprocess


SCRIPT_PATH = "/nfs/scripts/automation/playbooks/shutdown.yml"

# ansible-playbook playbooks/shutdown.yml --extra-vars "target=johnny06"


def shutdown(node_number):
    """
    The actual functionality of the script
    """
    return _exec_ansible(SCRIPT_PATH, "--extra-vars", f'"target=johnny0{node_number}"')


def _exec_ansible(cmd, *args):
    """
    Executes the bash script with argument, handling any errors
    Returns a tuple with boolean result and error string, if any
    :param cmd:
    :param args:
    :return:
    """
    result = False
    error = None

    # ssh bobby sudo SCRIPT_PATH ARGS
    try:
        # run ssh with pjamaadmin to execute the command on bobby using sudo
        child = subprocess.Popen(
            ["sudo", "-u", "pjamaadmin", "ssh", "bobby", "ansible-playbook", cmd, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        _, error_stream = child.communicate()
        if not child.returncode:
            result = True
        else:
            error = error_stream.decode("ascii")

    except Exception as e:
        error = str(e)

    return result, error


def main(node_number: int) -> dict:
    """
    Entry point of the script (from external location)
    """
    result, error = shutdown(node_number=node_number)

    response = {"action": "shutdown", "target": node_number}

    if not result:
        response["result"] = "failed"
        if error:
            response["error"] = error
    else:
        response["result"] = "success"

    return response


if __name__ == "__main__":
    """
    When running the script manually (takes arguments from stdin)
    """
    if len(sys.argv) != 2:
        raise ValueError("Shutdown is expecting exactly 1 argument!")

    print(main(sys.argv[1]))

