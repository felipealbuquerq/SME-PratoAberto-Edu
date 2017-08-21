import json

from celery import Celery
from flask import Flask, request

from workers import process_message, FB_VERIFY_TOKEN, FB_TOKEN


app = Flask(__name__)


@app.route('/telegram', methods=['POST'])
def telegram():
    process_message.delay(json.loads(request.data.decode()))
    process_message.delay({'source': 'telegram', 'data': json.loads(request.data.decode())})
    return ('', 204)


@app.route('/facebook', methods=['GET', 'POST'])
def facebook():
    if request.method == 'POST':
        process_message.delay({'source': 'facebook', 'data': json.loads(request.data.decode())})
        return ('', 204)
    elif request.method == 'GET': # Para a verificação inicial
        if request.args.get('hub.verify_token') == FB_VERIFY_TOKEN:
            return request.args.get('hub.challenge')
        return "Wrong Verify Token"

if __name__ == '__main__':
    app.run()
