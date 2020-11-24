#!/env/python
import os
import sys

from pathlib import Path

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_keys_from_file(path):
    env_keys = []
    with open(path) as env_file:
        for line in env_file:
            key = line.split("=")[0]
            env_keys.append(key.strip())
    return env_keys


def get_user_env_file_path():
    env_file_path = str(Path.home())+"/.lifeloopenv"
    if os.path.isfile(env_file_path):
        return env_file_path
    print("No lifeloopweb .env file found in at $HOME/.lifeloopenv.  "
          "Please run "
          "`cp .env.template ~/.lifeloopenv && ln -s ~/.lifeloopenv .env` "
          "from application root directory.")
    sys.exit(1)


def compare_keys(keys1, keys2):
    return [item for item in keys1 if item not in keys2]

def main():
    env_template_file_path = os.path.join(CURRENT_DIR, '../.env.template')
    mandatory_keys = get_keys_from_file(env_template_file_path)
    user_env_file_path = get_user_env_file_path()
    print("Found env file at {}".format(user_env_file_path))
    user_keys = get_keys_from_file(user_env_file_path)
    missing_keys = compare_keys(mandatory_keys, user_keys)
    if missing_keys:
        print("The following keys are missing from your env file: {}".format(
            ",".join(missing_keys)))
        sys.exit(1)
    print("Your env file is not missing any keys")


if __name__ == "__main__":
    main()
