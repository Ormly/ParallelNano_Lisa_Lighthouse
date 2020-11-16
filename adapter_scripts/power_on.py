import sys
import subprocess


SCRIPT_PATH = "/nfs/scripts/automation/lisa_scripts/power_control.py"


def power(username, password):
    """
    The actual functionality of the script
    """
    return _exec_bash(SCRIPT_PATH, "-u", username, password)


def create_admin(username, password):
    """
    The actual functionality of the script
    """
    return _exec_bash(SCRIPT_PATH, "-a", username, password)


def _exec_bash(cmd, *args):
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
            ["sudo", "-u", "pjamaadmin", "ssh", "bobby", "sudo", cmd, *args],
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


def main(username, password, user_type) -> dict:
    """
    Entry point of the script (from external location)
    """
    if user_type == "user":
        result, error = create_user(username, password)
    else:
        result, error = create_admin(username, password)

    response = {"action": "create_user", "target": username, "type": user_type}

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
    if len(sys.argv) != 4:
        raise ValueError("Create user is expecting exactly 3 arguments!")

    if sys.argv[3] not in ["admin", "user"]:
        raise ValueError("User type is expected to be either 'user' or 'admin'!")

    print(main(sys.argv[1], sys.argv[2], sys.argv[3]))

