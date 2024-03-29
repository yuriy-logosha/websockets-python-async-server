#!/usr/bin/env python

import asyncio
import json
import logging.handlers
import websockets
import uuid
import socket
import sys
import datetime as dt


def myip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


USERS = set()
default_port = 1300
params = {}
params.update({'remote': myip()})

if sys.argv:
    for idx in range(1, sys.argv.__len__()):
        key, value = [i.strip() for i in sys.argv[idx].split('=', 1)]
        params.update({key: value})


class MyFormatter(logging.Formatter):
    converter = dt.datetime.fromtimestamp

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y-%m-%d %H:%M:%S:%f")
            s = "%s,%03d" % (t, record.msecs)
        return s


Logger = logging.getLogger('websocket-server')
Logger.setLevel(logging.DEBUG)
formatter = MyFormatter(fmt='%(asctime)s %(levelname)s %(name)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S:%f')
console = logging.StreamHandler()
console.setFormatter(formatter)
file_handler = logging.handlers.RotatingFileHandler(params.get('LOG_FILENAME', 'server.log'), maxBytes=1024*10, backupCount=5)
file_handler.setFormatter(formatter)

Logger.addHandler(file_handler)
Logger.addHandler(console)


def user_to_json(user):
    _u = {'type': 'user', 'uuid': user.uuid, 'port': user.service_port}
    if user.custom_fields:
        for custom_field in user.custom_fields:
            if hasattr(user, custom_field):
                _u[custom_field] = getattr(user, custom_field)
    return _u


def users_to_json():
    result = []
    for user in USERS:
        if hasattr(user, 'name'):
            result.append(user_to_json(user))
    return result


async def notify_users():
    if USERS:
        message = json.dumps({'type': 'users', 'users': users_to_json()})
        await asyncio.wait([user.send(message) for user in USERS])


async def get_user(uuid):
    if USERS:
        for user in USERS:
            if user.uuid == uuid:
                return user


def handle(user):
    try:
        for message in user.messages:
            print(message)
    except Exception as exc:
        Logger.error(exc)


async def register(user):
    user.uuid = str(uuid.uuid1())
    user.service_port = default_port + 1 + len(USERS)
    user.custom_fields = set()
    user.results = []
    USERS.add(user)
    Logger.info("Register: %s", user.uuid)
    msg = json.dumps({'type': 'settings', 'uuid': user.uuid, 'port': user.service_port})
    await user.send(msg)
    await notify_users()


async def unregister(user):
    Logger.info("Unregister: %s", user.uuid)
    USERS.remove(user)
    await notify_users()


def parse(message):
    return json.loads(message)


def get_result(results, _id):
    for r in results:
        if r["id"] == _id:
            return r
    return None

def build_container(type, value):
    return {'type': type, type: value}

async def serve(websocket, path):
    try:
        await register(websocket)
        async for message in websocket:
            Logger.info('Received %s from %s' % (message, websocket.uuid))
            try:
                data = parse(message)
                if data['type'] == "name":
                    websocket.name = data['name']
                    websocket.custom_fields.add('name')
                    await notify_users()
                elif data['type'] == "status":
                    r = get_result(websocket.results, data["id"])
                    if r:
                        r['result'] = data['status']
                        r['status'] = 'DONE'
                        user = await get_user(r['to'])
                        await user.send(json.dumps(build_container('status-container', r)))
                elif data['type'] == "result" and data['id']:
                    r = get_result(websocket.results, data["id"])
                    if r:
                        r['result'] = data['result']
                        r['status'] = data['status']
                        if data['status'] is 'DONE':
                            websocket.results.remove(r)
                        user = await get_user(r['to'])
                        await user.send(json.dumps(build_container('result-container', r)))
                    
                elif data['type'] == "command" and data['to'] and data['id']:
                    user = await get_user(data['to'])
                    if not user:
                        Logger.info("User not found by uuid %s", data['to'])
                        await websocket.send("User not found by uuid " + data['to'])
                    else:
                        result = {
                            'type': 'result',
                            'id': data['id'],
                            'status': 'SENDING',
                            'to': websocket.uuid,
                            'from': data['to'],
                            'result': ''}
                        
                        user.results.append(result)
    
                        Logger.info("Sending to %s %s", user.name, data)
                        await user.send(json.dumps(data))
                        await websocket.send(json.dumps(build_container('result-container', result)))
            except Exception as pex:
                Logger.error("Parsing Exception", pex)

    except Exception as ex:
        Logger.error(ex)
    finally:
        await unregister(websocket)


_host = params.get('remote', 'localhost')
_port = params.get('port', default_port)
asyncio.get_event_loop().run_until_complete(websockets.serve(serve, host=_host, port=_port))
Logger.info("Started on port %s for %s.", _port, _host)
asyncio.get_event_loop().run_forever()
