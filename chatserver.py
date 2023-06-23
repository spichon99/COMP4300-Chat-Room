# COMP 4300 - Computer Networks
# Assignment 1
# Sebastien Pichon 7840237
#
# Chat Server:
#   - View list of existing chat rooms
#   - View number and list of connceted users for each room
#   - Join existing chat rooms if they're not full (max 5 users)
#   - Create chat rooms
#   - Send messages to chat rooms
#   - Leave a chat room

# Chat commands:
# /help: lists all commands
# /exit: exit everything and stop the program
# /list: list existing chat rooms
# /create: create a new chat room
# /join <room #>: join the specified room
# /leave: leave the current room if in one
#
# Lobby will be room 0, should not hear messages from anyone else in the lobby

import sys
import socket
import threading
import json
import os

MAX_CAPACITY = 5    #most people allowed in a room
DEFAULT_PORT = 8433 #default port that is used if none is given

#arrays    
clients = []
rooms = []

# == classes ==
class Room:
    def __init__(self,number):
        self.number = number    #the room number
        self.clients = []       #all clients in that room, up to MAX_CAPACITY should be allowed
        
class Client:
    def __init__(self,sock,address,room,username):
        self.sock = sock
        self.address = address
        self.room = room        # this is a room number, not the object
        self.username = username


# == helper functions ==
def getRoomNumber(room): #used to sort the room.client array
    return room.number
    
def findRoomByNumber(roomNumber): #returns the room object matching the given room number
    #iterate through array of rooms until find one matching the room number, return -1 if can't find it
    return next((r for r in rooms if r.number == roomNumber),-1) 
    
def serverMessage(message): #takes a string and turns it into the appropriate json message being sent by the server
    messageObj = {"username":"server","message":message}
    return json.dumps(messageObj)
        


# == Creating the server socket ==
HOST = ''   #just use the computer this program is running on
try:
    PORT = int(sys.argv[1])
except:
    PORT = DEFAULT_PORT #default port if none is given
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST,PORT))
server.listen()


# == server chat room functions ==
def broadcast(message,room):
    #send to everyone in the same room (that isn't lobby)
    if room != 0:
        for client in clients: #iterate through clients array
            if client.room == room: #if that client is in the given room, send them the message
                client.sock.send(message)

def handleLeaveRoom(roomNumber,client): #called any time a client leaves a given chat room
    if roomNumber != 0: #not in lobby
        room = findRoomByNumber(roomNumber) #get the specified room from the array
        print("Client was in room #"+str(roomNumber)+" with "+str(len(room.clients))+" clients") #for debugging
        if room == -1:
            print("room number is -1") #error handling
        else:
            room.clients.remove(client) #remove this client from the room's client array
            if len(room.clients) == 0: #they were the last client in that room, so delete the room now that it's empty
                rooms.remove(room)
        
def handleClient(client): #a thread is created for every new client running this function on a loop
    print("handling client: "+str(client.address))
    while True:
        try: #commands + messages
            message = client.sock.recv(1024)
            messageObj = json.loads(message)
            
            msg = messageObj["message"]
            
            #TODO: clean this up
            if msg.lower().startswith("/"): #commands
                command = msg.lower()
                
                if command.startswith("/exit"): #disconnect from server
                    username = client.username
                    roomNumber = client.room
                    handleLeaveRoom(roomNumber,client)
                    print(username+" has disconnected. (/EXIT)")
                    client.sock.close()
                    clients.remove(client)
                    toSend = serverMessage(client.username+" has disconnected.")
                    broadcast(toSend.encode(),roomNumber) #let that room know they disconnected.
                    break
                    
                elif command.startswith("/join"): #change the client's room number
                    cmd = command.split(' ') #to get the second argument in the command
                    if len(cmd)<2: #only typed '/join', need to include a number as well
                        toSend = serverMessage("Invalid use of join command. Missing room number.")
                        client.sock.send(toSend.encode())
                    elif not cmd[1].isdigit(): #the second argument wasn't a number
                        toSend = serverMessage("Please enter a valid digit.")
                        client.sock.send(toSend.encode())
                    else:
                        print("Client would like to join room "+str(cmd[1])) #for debugging
                        #check if there's room for a client to join (or if the room exists)
                        room = findRoomByNumber(int(cmd[1])) #this is the room  #next((r for r in rooms if r.number == int(cmd[1])),-1)
                        if room == -1: #did not find specified room in the rooms array
                            print("Room was not found.")
                            toSend = serverMessage("Room was not found")
                            client.sock.send(toSend.encode()) #let user know that room doesn't exist
                        elif int(cmd[1]) == client.room: #trying to join room the client is already in
                            print("Client attempting to join room they are already in.")
                            toSend = serverMessage("You are already in that room.")
                            client.sock.send(toSend.encode())
                        elif len(room.clients)>=MAX_CAPACITY: #room is full, don't let them join
                            toSend = serverMessage("Could not join. Room #"+str(room.number)+" is full.")
                            client.sock.send(toSend.encode())
                        else: #no problems, should be able to join the room
                            room.clients.append(client)
                            handleLeaveRoom(client.room,client) #leave the last room this client was in
                            toSend = serverMessage(client.username+" has joined the room.")
                            broadcast(toSend.encode(),int(cmd[1])) #tell everyone in the room that a client has joined
                            client.room = int(cmd[1])
                            print("client "+client.username+"'s room number is now : "+str(client.room)) #for debugging
                            toSend = serverMessage("Successfully joined room #"+str(client.room))
                            client.sock.send(toSend.encode()) #let the client know that they have joined successfully
                
                elif command.startswith("/leave"):
                    if client.room == 0:
                        toSend = serverMessage("Cannot leave the lobby")
                        client.sock.send(toSend.encode())
                    else:
                        oldRoom = client.room
                        client.room = 0 #set client room to 0 (lobby)
                        room = findRoomByNumber(oldRoom)
                        
                        toSend = serverMessage(client.username+" has left the room. "+str(len(room.clients)-1)+"/"+str(MAX_CAPACITY))
                        broadcast(toSend.encode(),oldRoom) #send to everyone in the room after this client has left
                        handleLeaveRoom(oldRoom,client) #handle leaving the room
                        toSend = serverMessage("Left room #"+str(oldRoom)+". Use '/list' to view existing rooms or '/help' for other commands.")
                        client.sock.send(toSend.encode()) #let the client know that they have left successfully
                        
                elif command.startswith("/help"): #show valid commands
                    bigStr = "Valid commands:\n"
                    bigStr += "/help: Shows valid commands\n"
                    bigStr += "/exit: Disconnect from server\n"
                    bigStr += "/create: Create a new chat room\n"
                    bigStr += "/list: List existing rooms\n"
                    bigStr += "/join <#>: Join an existing room\n"
                    bigStr += "/leave: Leave the current room, bringing you back to the lobby"
                    toSend = serverMessage(bigStr)
                    client.sock.send(toSend.encode())
                    
                elif command.startswith("/create"): #Create a new chat room
                    print("Creating new room...")
                    oldRoomNumber = client.room #saving what room they were in before to delete the room if nobody is left
                    #find lowest room number that is not in use
                    newRoomNumber = 1
                    print("newRoomNumber = "+str(newRoomNumber))
                    if len(rooms)>0:
                        for room in rooms:
                            if newRoomNumber == room.number:
                                newRoomNumber += 1
                    print("Room number will be #"+str(newRoomNumber)) #debug
                    #add to rooms array and put client in that rooms client array
                    newRoom = Room(newRoomNumber)
                    rooms.append(newRoom)
                    newRoom.clients.append(client)
                    client.room = newRoomNumber
                    #if let everyone know in old room that this client has left
                    oldRoom = findRoomByNumber(oldRoomNumber)
                    if oldRoom != -1: #happens when creating a room from the lobby don't worry about it
                        toSend = serverMessage(client.username+" has left the room. "+str(len(oldRoom.clients)-1)+"/"+str(MAX_CAPACITY))
                        broadcast(toSend.encode(),oldRoomNumber)
                    #if old room is now empty, delete it
                    handleLeaveRoom(oldRoomNumber,client)
                    rooms.sort(key=getRoomNumber) #sort array by room number
                    toSend = serverMessage("Successfully created room #"+str(newRoomNumber))
                    client.sock.send(toSend.encode())
                    
                    
                elif command.startswith("/list"):
                    bigStr = "===== ROOMS =====\n"
                    if len(rooms)>0: #if there are any rooms
                        for r in rooms:
                            bigStr += "ROOM "+str(r.number)+" : "+str(len(r.clients))+"/"+str(MAX_CAPACITY)+"\n" #print room # and current capacity
                            for c in r.clients:
                                bigStr += " - "+c.username+"\n" #show list of users in the room
                    else: #there aren't any rooms
                        bigStr += " No rooms currently exist. Create one using '/create'\n"
                    bigStr += "================="
                    toSend = serverMessage(bigStr)
                    client.sock.send(toSend.encode())
                
                elif command.startswith("/clientlist"): #for debugging
                    bigStr = "===== CLIENTS =====\n"
                    for c in clients:
                        print("c: "+c.username)
                        print("Client "+c.username+" is in room "+str(c.room))
                        bigStr += "Client "+c.username+" is in room "+str(c.room)+"\n"
                    bigStr += "==================="
                    toSend = serverMessage(bigStr)
                    client.sock.send(toSend.encode())
                
                elif command.startswith("/roomlist"): #for debugging but entirely unneeded now
                    bigStr = "===== ROOMS =====\n"
                    if len(rooms)>0:
                        for r in rooms:
                            print("r: "+str(r.number))
                            numClients = len(r.clients)
                            bigStr += "r: "+str(r.number)+" has "+str(numClients)+" clients\n"
                    bigStr += "================="
                    toSend = serverMessage(bigStr)
                    client.sock.send(toSend.encode())
                
                else: #command did not match any other commands
                    toSend = serverMessage("Invalid command. For help type '/help'")
                    client.sock.send(toSend.encode())
            else: #its a regular message, send it to everyone in the appropriate room
                print("["+str(client.room)+"]"+messageObj["username"]+"> "+messageObj["message"]) #for debugging, shows room #, username, and message
                broadcast(message,client.room)
                
        except Exception as e: #disconnect if an error happens
            username = client.username
            print(username+" has disconnected. (ERROR)")
            print(e)
            handleLeaveRoom(client.room,client)
            client.sock.close()
            clients.remove(client)
            break
    #sys.exit(0)
            
def receiveClients():
    print("Server is listening on "+str(socket.gethostname())+":"+str(PORT))
    while True:
        try:
            #accept connections
            client, address = server.accept()
            print("Connected with "+str(address))
            
            #get the client's username
            messageObj = {"username":"server","message":"username"}#special server message to prompt getting the username
            messageObj = json.dumps(messageObj)
            client.send(messageObj.encode())
            
            username = client.recv(1024).decode()
            username = json.loads(username)
            username = username["username"]
            
            #make a client object to store all the needed information
            newClient = Client(client,address,0,username) #they start in room 0 (the lobby)
            clients.append(newClient)
            print("Client created ("+username+")")
            
            #let the client know they've connected and how to use the program
            toSend = serverMessage("Connected to server. Use '/help' to view a list of commands.")
            client.send(toSend.encode())
            #create a new thread for each client
            thread = threading.Thread(target=handleClient, args=(newClient,),daemon=True)
            thread.start()
        except socket.timeout as e:
            print('timeout')
            pass
        except KeyboardInterrupt as e:
            print("Shutting down server...")
            server.close()
            sys.exit(0)
        except Exception as e:
            print("Something happened... I guess...")
            print(e) #print to figure out what went wrong
            server.close()
            sys.exit(-1)

#start the program loop        
receiveClients()