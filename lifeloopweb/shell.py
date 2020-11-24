# pylint: disable=wrong-import-position,unused-import
import os
import sys


import dotenv
from ptpython import ipython

# TODO Move this into the code base
# Define it with an entry point
# Our overarching "framework" should be able to just find shells by entrypoint
# and let you run said shell. It shouldn't be in the Makefile

config = ipython.load_default_config()
config.InteractiveShellEmbed = config.TerminalInteractiveShell
shell = ipython.InteractiveShellEmbed.instance(config=config)
ipython.initialize_extensions(shell,
                              config['InteractiveShellApp']['extensions'])

env_file = sys.argv[1] if len(sys.argv) > 1 else ".env"

full_path = os.path.abspath(os.path.expanduser(env_file))
if not os.path.exists(full_path):
    raise Exception("Cannot find an environment file named "
                    "'{}'".format(full_path))

print("Loading env file: {}".format(full_path))
dotenv.load_dotenv(full_path)


def main():
    shell(header='', stack_depth=1, compile_flags=None)


if __name__ == "__main__":
    main()
