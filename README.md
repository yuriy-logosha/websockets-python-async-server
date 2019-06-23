# Websockets-python-async-server
Server on websockets for **Python3**. It's collecting all connections into set with several custom attributes: uuid, name, status, etc.

#Features
Notify users if new user have came/left or status has changed.

# Defaults
- Server accessible outside. Add attribute host=localhost to override and make it accessible only locally.
- Default port 1300. Add attribute port=<port_number> to override.
- Default logging level: INFO

# How to run?
1. Get server.py
2. Execute script: "python server.py"
3. To run it from pm2: "pm2 start server.py --interpreter=python3"

# How to use?
Send it a **JSON** to establish a connection. 
It will answer with response:
    `{'type': 'settings', 'uuid': <generated_uuid>, 'port': <service_port>}`
where:
- generated_uuid - is unique id of connection;
- service_port - private communication port (not used for now)

#### Example 1:
`{'type':'name', 'name':<any_name>}` - a new name will be give to connection.

#### Example 2: 
`{'type':'status', 'status':'<any_string>', 'queue':'<any_list>', 'current':'<any_string>'}` - a new status will be saved to connection.
- key `status` - can represent current status of client;
- key `queue` - any internal list or sequence to share with others, e.g. list of future commands;
- key `current` - any characters to describe current situation.

#### Example 3: 
`{'type':'command', 'command':'<any_string>', 'uuid':'<any_string>'}` - send the "command" directly to connection with the "uuid". If connection with the uuid not found - ignore it.
