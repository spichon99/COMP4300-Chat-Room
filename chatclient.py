# COMP 4300 - Computer Networks
# Assignment 1
# Sebastien Pichon 7840237
#
# Chat Client:
#   - View list of existing chat rooms
#   - View number and list of connceted users for each room
#   - Join one or more existing chat rooms if there's room
#   - Create chat rooms
#   - Send messages to chat rooms
#   - Leave a chat room

import socket
import sys
import json
import threading

HOST = ''       # default host
PORT = 8433     # default port used by the server

if len(sys.argv) >= 2: # can specify host in command line
    HOST = sys.argv[1]
if len(sys.argv) >= 3: # can specify port in command line
    PORT = int(sys.argv[2])
    
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST,PORT))

username = ''

while True: #do while loop
    username = input('Enter your username: ') #should reserve a username for the server, don't let client pick that username
    if username != 'server':
        break
    print('Username may not be server.\n') # let client know that username is reserved
    
    
def receive():
    while True:
        try:
            data = client.recv(1024).decode('utf-8')
            message = json.loads(data)
            
            if message["username"] == "server": #from server
                if message["message"] == "username": #special case: server is asking for username
                    messageObj = {"username":username,"message":username}
                    asJson = json.dumps(messageObj)
                    client.send((asJson).encode())
                else:
                    print(message["message"]) #just print the message
            else: #regular message, print it
                print(message["username"]+"> "+message["message"]) #include username because this is from another client
        except:
            print("Disconnecting.") #goodnight sweet prince, this happens when you use /exit to disconnect
            client.close()
            break


def sendMessages():
    while True:
        try:
            message = input(); 
            messageObj = {"username":username,"message":message} #send as json to send both username and the message
            asJson = json.dumps(messageObj);
            client.sendall(asJson.encode())
        except Exception as e:
            print("error. stopping send thread.")
            print(e)
            pass
            
#start two threads, one for receiving messages and one for sending messages            
rThread = threading.Thread(target=receive)
rThread.start()
sThread = threading.Thread(target=sendMessages,daemon=True) #make sure this thread dies when the other one does i hope
sThread.start()

