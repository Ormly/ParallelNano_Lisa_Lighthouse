import sys
import subprocess


SCRIPT_PATH = "/nfs/scripts/automation/remove_user.bash"


def remove_user(username):
    """
    The actual functionality of the script
    """
    return _exec_bash(SCRIPT_PATH, username)


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

    try:
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


def main(username) -> dict:
    """
    Entry point of the script (from external location)
    """

    response = {"action": "remove_user", "target": username}

    result, error = remove_user(username)

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
        raise ValueError("Remove user is expecting exactly 1 arguments!")

    print(main(sys.argv[1]))

