#!/usr/local/bin/python

import datetime
import os
import shlex
import subprocess
import sys
import tempfile
import traceback

import requests
import tinys3


MAILGUN_REQUEST_URL = 'https://api.mailgun.net/v3/{}/messages'


def send_mail(body):
    api_key = os.environ.get("MAILGUN_API_KEY")
    domain = os.environ.get("MAILGUN_DOMAIN")
    mail_from = os.environ.get("DB_ADMIN_EMAIL")
    mail_to = os.environ.get("LOGGING_ADMINS")
    url = MAILGUN_REQUEST_URL.format(domain)
    current_time = str(datetime.datetime.now().strftime("%m-%d-%Y %H:%M"))
    subject = "Backup Failure {}".format(current_time)
    print("Sending email from '{}' to '{}'".format(mail_from, mail_to))
    print("POST", url)
    request = requests.post(url,
                            auth=('api', api_key),
                            data={'from': mail_from,
                                  'to': mail_to,
                                  'subject': subject,
                                  'html': body})
    if request.status_code != 200:
        print("Mailgun POST failed, status code", request.status_code)
        print("Request URL", url)
        print(request.text)

    return request.status_code == 200


def run_command(cmd, path, timeout=60):
    try:
        cmd = shlex.split(cmd)
        with open(path, 'wb') as f:
            f.write(subprocess.check_output(cmd,
                                            stderr=subprocess.STDOUT,
                                            timeout=timeout))
    except Exception:
        exc = traceback.format_exc()
        print(exc)
        send_mail(str(exc))
        return False
    return True


def upload(path, access_key, secret_key, bucket_name, folder_name):
    print("Uploading {} to {}".format(path, bucket_name))
    conn = tinys3.Connection(access_key, secret_key, tls=True,
                             default_bucket=bucket_name)
    upload_name = os.path.join(folder_name, os.path.split(path)[-1])
    print("Upload name is {}".format(upload_name))
    with open(path, 'rb') as f:
        resp = conn.upload(upload_name, f)
        if not (resp and resp.status_code == 200):
            print("Failed to upload '{}'".format(path))
            if resp:
                print("Error: {}".format(resp.data))
                # TODO This needds to notify, send an email, something.
                sys.exit(2)
        print("'{}' uploaded successfully to bucket '{}'".format(path, bucket_name))


def backup_db(db_host, db_name):
    backup_file = "{}_{}.sql".format(db_name,
                                     datetime.datetime.now().strftime(
                                         "%Y_%m_%d_%H%M%S"))
    path = os.path.join(tempfile.gettempdir(), backup_file)
    if not run_command("mysqldump -h {} --databases {}".format(db_host,
                                                               db_name), path):
        print("Couldn't backup the database, quitting...")
        sys.exit(2)
    return path


def main():
    env_vars = ["DATABASE_NAME", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
                "AWS_BUCKET_NAME", "DATABASE_HOSTNAME", "MAILGUN_DOMAIN",
                "MAILGUN_API_KEY", "DB_ADMIN_EMAIL",
                "LOGGING_ADMINS"]
    missing = []
    for v in env_vars:
        if not os.environ.get(v):
            missing.append(v)

    if missing:
        print("The following env vars are missing or have no value, "
              "and must be set: {}".format(', '.join(missing)))
        sys.exit(1)

    db_host = os.environ["DATABASE_HOSTNAME"]
    db_name = os.environ["DATABASE_NAME"]
    access_key = os.environ["AWS_ACCESS_KEY_ID"]
    secret_key = os.environ["AWS_SECRET_ACCESS_KEY"]
    bucket_name = os.environ["AWS_BUCKET_NAME"]
    folder_name = "backups"
    backup_path = backup_db(db_host, db_name)
    upload(backup_path, access_key, secret_key, bucket_name, folder_name)

if __name__ == "__main__":
    main()
