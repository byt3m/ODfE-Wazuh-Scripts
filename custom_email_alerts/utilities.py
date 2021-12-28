#!/usr/bin/python3

import os
import datetime
import json


def save_file_to_disk(content, path):
    # Save data to disk
    check_file_exists(path, create=True)
    append_file(path, content)


def get_files_by_extension(path, extension):
    return [_ for _ in os.listdir(path) if _.endswith(extension)]


def read_text_file(path):
    with open(path, "r") as f:
        return f.read()


def read_json(path):
    with open (path, "r") as f:
        return json.load(f)


def get_script_path_from_args(path):
    return os.path.abspath(os.path.dirname(path))


def get_time_now():
    now = datetime.datetime.now()
    return now.strftime('%Y-%m-%d %H:%M:%S')


def append_file(file, text):
    with open(file, "a") as f:
        f.write(text + "\n")


def check_file_exists(file, create=False):
    if not os.path.exists(file):
        if create:
            with open(file, "w") as f:
                f.write("")


def log(text, file):
    check_file_exists(file, create=True)
    append_file(file, text)
