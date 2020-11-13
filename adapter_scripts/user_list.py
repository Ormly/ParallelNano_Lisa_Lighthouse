import os


def get_users():
    """
    The actual functionality of the script
    """
    users = []
    try:
        stream = os.popen("/nfs/scripts/automation/get_users.bash")
        for line in stream.readlines():
            users.append(line.rstrip())
    except Exception:
        users = None
        pass
    return users


def main() -> dict:
    """
    Entry point of the script (from external location)
    """
    users = get_users()
    response = {"action": "get_users", "users": users}

    if users is None:
        response["result"] = "failed"
    else:
        response["result"] = "success"

    return response


if __name__ == "__main__":
    """
    When running the script manually (takes arguments from stdin)
    """
    print(main())

