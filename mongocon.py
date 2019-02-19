# -*- coding: utf-8 -*-
from pymongo import MongoClient

from celeryconfig import MONGO_URL, APP_NAME


def new_client():
    client = MongoClient(MONGO_URL)
    db = client[APP_NAME]
    return db
