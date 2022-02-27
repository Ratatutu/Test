from flask import Flask,request,jsonify
import os

app=Flask(__name__)

@app.route("/")
def index():
    return "Hello World oaweigiwebgoaweb!"


hostIP="0.0.0.0"
hostPort=os.environ.get("PORT",5000)
if(__name__=="__main__"):
  print("Starting up in main...")
  app.run(host=hostIP,port=hostPort)
