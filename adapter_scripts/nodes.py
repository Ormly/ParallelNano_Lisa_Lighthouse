"""
Returns the list of compute node names that are expected to be present in this setup
"""


def get_nodes():
    """
    The actual functionality of the script
    """
    return ["johnny0" + str(i) for i in range(1, 7)]


def main() -> dict:
    """
    Entry point of the script (from external location)
    """
    return {"action": "nodes", "nodes": get_nodes(), "result": "success"}


if __name__ == "__main__":
    """
    When running the script manually (takes arguments from stdin)
    """
    print(main())

