#===================================================================#
# (Mass amount of )Imports
#===================================================================#
from pathlib import Path
from flask import Flask,jsonify,request
import threading
import logging
from numpy import tracemalloc_domain
from snapi_py_client.snapi_bridge import StocknoteAPIPythonBridge
import datetime
from datetime import datetime as _datetime
from datetime import date
from tabulate import tabulate
from time import sleep
import json
import pandas as pd
import requests
import time
import pathlib
import traceback
import os

# print("Done with imports")
#===================================================================#
# Constants
#===================================================================#

#=================
# Debug stuff
#=================
# Debug errors?  Currently not used since release build
#debugErrs = False

# Do you want to show the CE n PE count to check whether it is right or not??
displayCount = False

#=================
# Initial stuff
#=================
# Login details
loginDetails = {'userId':   'RJ31740'
                ,'password': 'Byte@123'
                ,'yob':      '1985'}
# Providing the expiry date manually
# This is only recommended to do if ure SURE of the expiry
# The format is manualExpiry = ["DD-Mon-YYYY"]
manualExpiry = None
manualExpiry = ["03-Mar-2022"]
# The range to count from the center strike price option
#count_range=2 at strikePriceOption 38000, it'd sum from 37800 to
# 38200 (Which is 2*count_range+1=2*2+1=5 options total)
# Any number on or above 100 will usually count ALL options
count_range = 100

#=================
# Server stuff
#=================
hostPort = os.environ.get("PORT",8000) #the custom port you want
hostIp = '0.0.0.0'

#=================
# Symbol stuff
#=================
# Symbol to use
symbol = 'BANKNIFTY'
# Symbol to use for getting index quotes
spot_symbol = "NIFTY BANK"

#=================
# Delay stuff
#=================
# Every dataRequestDelay seconds, it'll print your option data
dataRequestDelay = 60
#dataRequestDelay = 5

# How long before the webpage reloads (in milis)
# Defaulted to 0.5 second so it doesnt miss any reloads
# You can make this super low n itd be fine cuz of 2.4R update
# Basically even if therezz no new data itll send a blank msg rather than the
# entire html doc
webpageDataRequestDelay = 0.5 * 1000

# If a server requests gives an error, the next request will be sent after
# timeout_delay seconds (0.02 seems to be the sweetspot currently)
re_request_delay = 0.02

# Every writeLiveDataDelay seconds, live data is writen to the live data
# file
# NOTE: Currently this is a multiple of "delay" because it doesnt use threads
#       which is a slight problem but it is sumthin to just bear with for now
writeLiveDataDelay = 60

#=================
# Webpage stuff
#=================
# This is the order of the table headers
# You can move em around and itd prolly change nothing
# Removing them here is useless cuz they get added at the end if u do so
tableHeaders = ["LTT","SPOT","ATMsk","PrCls","LTP","CESum","PESum","Diff","NtDcy","Trend"]

# The following 2 values r to be taken from and ONLY from tableHeaders

# What do you want as the x Axis for the graph??
xHeader = "LTT"

# What do you want as the y Axis for the graph??  (Yd I type this even??)
yHeader = "Diff"

# How much the max/min y scale should be multiplied by
# If max value found is 13432 then it is multiplied by this and considered then
# max
# 1.07 seemzz chill
yAxisRangeMultiplier = 1.07

# Currently not working cuz Im dumm n too...  Idk...  I dont wanna do it lol...
# Who cares??....  Idve to change like 3-4 different aspects for this smh
# If you want to reverse the table rows
# (It will show the latest trend state on top if reverseDataLog=True)
# Only applies to the webpage/local server
#reverseDataLog = True

# Set this to a high number (60*60*6=21600 is the max ud need honestly) if u
# want to see the entire chart graph with ALL
# the data
dataOnGraphLimit = 50
dataOnGraphLimit = 21600

# Set this to 0 to have no animation when new values come up on the chart
# 250 seems to look decent
# 1s is the default from Chart.js
# (in millis)
chartAnimationTime = 250

#=================
# Printing stuff
#=================
# Clears the screen before printing new data
clearScreenEveryDelay = False

#=================
# Extra stuff
#=================
# If you want option chain details to be written to a file
writeOptionChainDetails = False

#=================
# NOT recommended to change stuff
#=================
# The following are things you might not want to change
# They have "__" before and after cuz u shouldnt need to modify them
# usually

# This is just a request code any value between 201-299 *SHOULD* be fine but
# why bother changing it when izz chillin??
noNewRowsCode = 256
# This is defaulted to 100 as every Option differs by 100
# Eg: 38000, then 38100, then 38200, etc
__diffBwFutures__ = 100
# File name for the live option data ("%s" is the date placeholder)
live_data_file_name = "OPTIDX_%s_RaMbo_Option_Data.csv"
# File name for the option chain details
option_chain_details_file_name = "Option_Chain_Details.txt"
# The url where you get the expiry dates from
expiry_url = 'https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY'

# print("Done with constants")
#====================================================================#
# Changelog
#====================================================================#
# 2.41R:
# > Reads data from excel now for the table
# 2.4R:
# > No more refreshing/reloading the ENTIRE page yay pog ggzz ez wp
# It only partly reloads for data => The table gets rows on request
# > Chart now has 2 datasets => 1 for +ve and 1 for -ve
# > Added a manual expiry check to make sure ure not putting the wrong one
# (Atleast logically)
# > Neatified tonna thingzz ig
# > Changed a few variable names to make em all right

#====================================================================#
# TODO
#====================================================================#
# 1 REMOVE all javascript comments cuz I think ure sending it to the asker....
# Yeah....  U are =-=
# 2 ALSO....  Obfuscate everything in js/html lmao....  U think data comezz
# free??  (Maybe a lil but cmawn)
# 3 How many rows an asker can take per request
# Good to limit so if they join randomly n have like 50k rows requirement,
# It'd send it slowly rather than all at once
# > Also, if the asker is not up to date, send them the latest rows
# > And then slowly send them the old rows
#rowCollectionBufferLimit=1024
# 4 Basically 3, but....  Currently it is workarounded to ask for the entire
# table (Every single row) on a refresh
# But you should just save it in a file stored inside the webpage somehow
# Gotta look into that file storage thing
#====================================================================#
__divider__ = "<------------->"
__safeExitMsg__ = __divider__ + "\nSafely Exiting\n" + __divider__
logger = logging.getLogger("werkzeug")
# Writes all the server related stuff into a separate log file rather than to
# console
logger.handlers = []
logger.addHandler(logging.FileHandler('flaskOutput.log'))

app = Flask(__name__)

tableRows = []
row_dict = {}
#====================================================================#
# Server stuff
#====================================================================#
connectedIPs = {}

@app.route('/',methods = ['GET','POST'])
def serverFunction():
    global webpageDataRequestDelay
    global xHeader,yHeader
    global noNewRowsCode
    global yAxisRangeMultiplier

    _ip = request.remote_addr
    _ip = request.environ['REMOTE_ADDR']
    
    if(_ip not in connectedIPs):
        print("[Server] New connection: ",_ip)
    else:
        print("[Server] IP",_ip,"requested webpage again. Possible reconnect. Had",connectedIPs[_ip],"rows (SS).\n Giving all rows at next request.")
    connectedIPs[_ip] = 0

    toReturn = '''<html>
    <head>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.4/Chart.js"></script>
    <script>
        var requestDelay=%s;
        var requester;
        var chartvas;
        var chart;
        var serverStatusDiv;
        var table;
        var tableHeader;
        var chx;
        var xAxisHeader="%s";
        var yAxisHeader="%s";
        var yAxisRangeMultiplier=%s;
        var xAxisIndex=-1;
        var yAxisIndex=-1;
        const serverStatusOnline=["ONLINE","00cc00"];
        const serverStatusDown=["DOWN","ff0000"];

        async function onServerStatus(reqObj,serverStatus,color){
            serverStatusDiv.innerHTML="<center>Server is <font color='"+color+"'><strong>"+serverStatus+"</strong></font> as of ["+(new Date().toLocaleString())+"] (RS: "+reqObj.readyState+", Status: "+reqObj.status+")</center>"
        }
        async function requestRows(){
            requester.onload = function() {
                if(this.status!=%s && (this.status == 0 ||(this.status >= 200 && this.status < 400))){
                    onServerStatus(this,serverStatusOnline[0],serverStatusOnline[1]);
                    jsonifiedData=JSON.parse(this.responseText);
                    console.log("Response:\\n"+this.responseText);
                    if(typeof(jsonifiedData["header"])!=="undefined"){
                        if(table.rows.length>0){
                            header=table.rows[0];
                            console.log("Resent header for some reason");
                        }else{
                            header=table.insertRow();
                        }
                        headerData=jsonifiedData["header"]

                        for(i=0;i<headerData.length;i++){
                            cell=header.insertCell();
                            cell.innerHTML=headerData[i];
                            if(xAxisHeader==headerData[i]){xAxisIndex=i;}
                            if(yAxisHeader==headerData[i]){yAxisIndex=i;}
                        }
                    }

                    rowsData=jsonifiedData["rows"];

                    insertedRows=0
                    for(i=0;i<rowsData.length;i++){
                        row=table.insertRow(1);
                        for(j=0;j<rowsData[i].length;j++){
                            cell=row.insertCell();
                            cell.innerHTML=rowsData[i][j];
                        }
                        insertedRows+=1;
                    }
                    for(i=0;i<rowsData.length;i++){
                        curRow=table.rows[rowsData.length-i];
                        yValue=(curRow.cells[yAxisIndex].innerHTML)
                                .replaceAll(",","");
                        
                        if(yValue>0){
                            chart.data.datasets[1].data.push(yValue);
                            chart.data.datasets[0].data.push(0);
                        }else{
                            chart.data.datasets[0].data.push(yValue);
                            chart.data.datasets[1].data.push(0);
                        }
                        
                        while(chart.data.datasets[0].data.length>%s){
                            chart.data.datasets[0].data.shift();
                            chart.data.datasets[1].data.shift();
                            chart.data.labels.shift();
                        }

                        console.log("YValue: "+yValue);
                        if(yValue!="Nan"){
                            chart.options.scales.yAxes[0].ticks.min=Math.min(chart.options.scales.yAxes[0].ticks.min,yValue*yAxisRangeMultiplier);
                            chart.options.scales.yAxes[0].ticks.max=Math.max(chart.options.scales.yAxes[0].ticks.max,yValue*yAxisRangeMultiplier);
                        }
                        tempLabel=curRow.cells[xAxisIndex].innerHTML;
                        if(typeof(tempLabel)=="number"){
                            tempLabel=Math.round(tempLabel);
                        }
                        chart.data.labels.push(tempLabel);
                    }
                    chart.update();
                }
                setTimeout(requestRows,requestDelay);
            }
            
            requester.open("POST", "table",true);
            requester.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
            requester.send(JSON.stringify({ "receivedCount": (table.rows.length-1)}));
        }
        function onLoad(){
            requester = new XMLHttpRequest();
            requester.onreadystatechange = function () {
                if(requester.readyState === XMLHttpRequest.DONE) {
                    var status = requester.status;
                    if (status === 0 || (status >= 200 && status < 400)) {
                        //console.log(requester.responseText);
                    } else {
                        console.log("Server is down");
                        //onServerStatus(this,serverStatusOnline[0],serverStatusOnline[1]);
                        onServerStatus(this,serverStatusDown[0],serverStatusDown[1]);
                    }
                }
            }
            requester.onerror = function(){console.log("Server is down");onServerStatus(this,serverStatusDown[0],serverStatusDown[1]);};

            chartvas = document.getElementById("chartvas");
            chx=chartvas.getContext("2d");
            chx.clear=function(){chx.clearRect(0,0,chx.canvas.width,chx.canvas.height);}
            chart = new Chart("chartvas",
            {
                type:"line",
                data: {
                    labels: [0],
                    datasets: [{
                        name:"negative",
                        fill:"origin",
                        lineTension:0,
                        backgroundColor: "rgba(255,0,0,0.5)",
                        borderColor: "rgba(255,0,0,0.7)",
                        data: [0]
                    },{
                        name:"positive",
                        fill:"origin",
                        lineTension:0,
                        backgroundColor: "rgba(0,255,0,0.5)",
                        borderColor: "rgba(0,255,0,0.7)",
                        data: [0]
                    }]
                },
                options: {
                    animation: {
                        duration: %s
                    },
                    plugins: {
                        filler: {propagate: true}
                    },
                    legend: {display: false},
                    scales: {
                        yAxes: [{ticks: {min: -3, max:+3}}],
                    }
                }
            })

            serverStatusDiv=document.getElementById("server-status-div");
            table=document.getElementById("table");

            requestRows();
        }
        document.onreadystatechange = function () {
          if (document.readyState == "complete") {
            onLoad();
          }
        }
    </script>
        <style>
        table {
                border-collapse: collapse;
                width: 100%%;
                font-family:Trebuchet MS;
            }
            th, td {
                border: 1px solid #ccc;
                padding: 10px;
            }
            tr:nth-child(even) {
                background-color: #dee2e6;
            }
            tr:nth-child(odd) {
                background-color: #ffffee;
            }
    </style><title>MetaBOSS</title>
    </head>
    <body>
    <form method="POST" action=".">
    <div id="server-status-div"></div>
    <canvas id="chartvas" style="overflow-y:scroll;width:100%%;height:50vh;"></canvas>
    <div style="overflow-y:scroll;height:40vh;"><table id="table"></table></div>
    </form>
    </body>
    </html>
    ''' % (webpageDataRequestDelay,xHeader,yHeader,yAxisRangeMultiplier,noNewRowsCode,dataOnGraphLimit,chartAnimationTime)
    return toReturn

# This is 2.4R being pog
# Just send a request to a sub page n get all the row table header data u want
# ezpz
@app.route('/table',methods = ['GET','POST'])
def tableRequested():
    global tableHeaders
    global tableRows
    global noNewRowsCode

    _ip = request.remote_addr
    _ip = request.environ['REMOTE_ADDR']
    toSend = {}
    if(_ip not in connectedIPs):
        # TODO
        # This is not technically a bug rn....  Has been workarounded to
        # actually give all rows....
        # This mainly happens when server restarts while clients r connected
        # So if it restarts u get EVERYTHING again
        # Which is kinda sad but it worxx for now cuz headers n rows r in
        # different dict keys
        print("[Server] >=> Something seems wrong. IP",_ip,"joined in weirdly. Note this down somewhere. Not super important but just weird.")
        connectedIPs[_ip] = 0
    
    if(request.method == "POST"):
        #print("Was given POST request")
        if("receivedCount" in request.json):
            clientRecCount = int(request.json["receivedCount"])
            if(clientRecCount <= 0):
                #print("Client has 0 rows and no header")
                clientRecCount = 0
            #print("receivedCount:",clientRecCount)
            connectedIPs[_ip] = clientRecCount

    # If the asker has no rows at all then provide with headers
    if(connectedIPs[_ip] == 0):
        #print("Somehow it became 0 for",_ip)
        toSend["header"] = tableHeaders
    #    print("Has 0 rows, provided with headers")
    #else:
    #    print("Rows collected:",connectedIPs[_ip])
    toSendRows = tableRows[connectedIPs[_ip]:]
    connectedIPs[_ip] += len(toSendRows)
    if(len(toSendRows) == len(tableRows)):
        #print("Providing with ENTIRE data")
        pass
    #print("Providing with",len(toSendRows),"rows out of",len(tableRows))
    if(len(toSendRows) == 0):
        return "",noNewRowsCode
    toSend["rows"] = toSendRows
    #print(str(toSend))
    return jsonify(toSend)

# Server status link
# Itll just ping back a 1 if the server is alive/running
@app.route('/status',methods=['GET'])
def serverStatus():
    return str(1 if serverThread.is_alive() else 0)

# The thread function that runs the server
def runServer():
    with app.test_request_context("/") as context:
        request.withCredentials = True
    app.run(host=hostIp, port=hostPort)

# Server thread....  Obvious....  Why am I writing this??
serverThread = threading.Thread(target=runServer)
# This makezz it so u dont needta task manager crouchjump wallrunning 180
# noscope force killpython.exe just to kill the forever running server
# Super helpful line ngl
serverThread.daemon = True

# print("Done with server stuff")
#====================================================================#
try:
    # 2.2R:
    # > Made the excel thing appendable rather than just overwriting old file
    #
    def formatINR(number):
        s, *d = str(number if number > 0 else -number).partition(".")
        r = ",".join([s[x - 2:x] for x in range(-3, -len(s), -2)][::-1] + [s[-3:]])
        return ("-" if number < 0 else "") + ("".join([r] + d))

    def myround(x, base=100):
        return int(base * round(float(x) / base))
    def roundBy(x,base=100):
        return round(float(x * base)) / base

    def get_expiries():
        print('Fetching expiries')
        if(manualExpiry is not None):
            print("Using provided manual expiry")
            # Convert expiry date to datetime object
            _expiryDate_ = _datetime.strptime(manualExpiry[0], '%d-%b-%Y')
            # Change time to right before end of trade day
            _expiryDate_ = _expiryDate_.replace(hour = 15,minute=30,second=1)
            # Check if the expiry date is ahead of current time
            if(_expiryDate_ < _datetime.now()):
                print("Or not.... You've provided an old manual expiry date")
                print("Please re-check and provide the right expiry date if you want it done manually")
                print("Trying to ACTUALLY fetch expiry now...")
            else:
                return manualExpiry
        page = ""
        headers = {
            'User-Agent':'Mozilla/5.0 (X11; CrOS x86_64 12871.102.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.141 Safari/537.36'
            #'User-Agent': 'Mozilla/5.0'
                    }
        while 1:
            try:
                page = requests.get(expiry_url, headers=headers)
                dajs = json.loads(page.text)
                expiry_dates = pd.DataFrame(dajs).loc[('expiryDates', 'records')]
                print('Received expiries')  
                return expiry_dates
            except json.decoder.JSONDecodeError:
                sleep(re_request_delay)
                continue
    def get_expiry_str_for_chain(expiry_date):
        #Reformats DD-MON-YYYY to YYYY-MM-DD for getting option chain data
        return _datetime.strftime(_datetime.strptime(expiry_date, '%d-%b-%Y'),"%Y-%m-%d")
    print(__divider__)
    print('Starting engine...')
    samco = StocknoteAPIPythonBridge()
    print('Logging in')
    while 1:
        try:
            login = samco.login(body=loginDetails)
            print('Fetching sessionToken')
            login = json.loads(login)
        except json.decoder.JSONDecodeError:
            sleep(0.1)
            continue
        break
    sessiontoken = login['sessionToken']
    samco.set_session_token(sessionToken=sessiontoken)

    expiry_dates = get_expiries()
    current_expiry_date = expiry_dates[0]
    
    # To send to samco for option chain data
    current_expiry_date_str = get_expiry_str_for_chain(current_expiry_date)

    print('Recent expiry =', current_expiry_date_str)

    now = _datetime.now()
    current_date = now.strftime('%d%b%y')
    print('Right now it is', now,'\n' + __divider__)
    start_time = now.replace(hour=0, minute=0, second=0)
    #start_time = now.replace(hour=9, minute=11, second=0)
    end_time = now.replace(hour=16, minute=30, second=0)
    live_data_file_name = live_data_file_name % current_date
    print("Live data file will be saved at",pathlib.Path(live_data_file_name).resolve())
    print("Option chain file will be saved at",pathlib.Path(option_chain_details_file_name).resolve())
    print(__divider__)
    previousHighprice = previousLowprice = 0
    major_df = pd.DataFrame()
    priorminute = -1
    initial = 0

    # Gets the futures symbol from optionChainDetails by stripping off the
    # strikePrice and the optionType
    def getFuturesSymbol(chainData):
        firstSymbol = chainData[0]
        return str(firstSymbol["tradingSymbol"]).replace(str(int(float(firstSymbol["strikePrice"]))),"").replace(firstSymbol["optionType"],"")

    headers = {
      'Accept': 'application/json',
      'x-session-token': sessiontoken
    }
    
    lastWrittenN = 0
    lastWriteTime = _datetime.now() - datetime.timedelta(seconds=writeLiveDataDelay + 1)

    # TODO Technically you should be putting this at the start cuz ud first
    # load everything from the system and THEN you do server stuff....  Cuz u
    # dont wanna do the bottleneck server stuff first and then waste time on
    # loading ezpz system file stuff right??
    if(os.path.exists(live_data_file_name)):
        live_data_file = open(live_data_file_name,"r")
        readData = live_data_file.readlines()
        live_data_file.close()
        _headerRow = True
        for i in readData:
            if(_headerRow):
                _headerRow = False
            else:
                if(i.endswith("\n")):
                    i = i[:-1]
                currentRow = i.split('","')
                for ei in range(0,len(currentRow)):
                    currentRow[ei] = currentRow[ei].replace('"',"")
                    try:
                        currentRow[ei] = float(currentRow[ei])
                    except:
                        pass
                # print("Current row of len",len(currentRow),":",currentRow)
                tableRows.append(currentRow)
                lastWrittenN+=1
        print("Added",len(tableRows),"rows from saved data file")

    firstTimeRun = True

    def getCombinedCEPEData(samcooo,symbol_n,exch,data_name):
        symbolCE = symbol_n + "CE"
        symbolPE = symbol_n + "PE"
        CEdata = getQuote(samco,symbolCE,exch) 
        PEdata = getQuote(samco,symbolPE,exch)
        return float(CEdata[data_name]) + float(PEdata[data_name])
    def getQuote(samcooo,symbol_n,exch):
        data = ""
        while 1:
            data = json.loads(samcooo.get_quote(symbol_name=symbol_n,exchange=(exch)))
            if("error" in data):
                sleep(re_request_delay)
                continue
            break
        return data

    if __name__ == '__main__':
        print("Starting server")
        serverThread.start()

    ithData = 0
    while now >= start_time:
        if start_time <= end_time:
            now = _datetime.now()
            lttStr=""
            chainStr = samco.get_option_chain(search_symbol_name=symbol, exchange=(samco.EXCHANGE_NFO), expiry_date=current_expiry_date_str)
            chain = json.loads(chainStr)
            if("error" in chain):
                sleep(re_request_delay)
                continue
            chain = chain["optionChainDetails"]
            if(writeOptionChainDetails):
                fil = open(option_chain_details_file_name,"w")
                fil.write(chainStr)
                fil.close()
            while 1:
                index_quote = requests.get('https://api.stocknote.com/quote/indexQuote',params={'indexName': spot_symbol}, headers = headers)
                index_quote = index_quote.json()
                if("error" in index_quote):
                    sleep(re_request_delay)
                    continue
                spot_price = float(index_quote['spotPrice'])
                lttStr =index_quote['lastTradedTime'].split(" ")[1]
                PrevClose_fut_price = spot_price - float(index_quote["change"])
                break
        
            nearest_expiry_price = myround(spot_price)
            nearest_Previousexpiry_price = myround(PrevClose_fut_price)

            if(firstTimeRun):
                firstTimeRun = False
                fut_symbol_base = getFuturesSymbol(chain)
                print("Fut_symbol:",fut_symbol_base)

                prevCloseSymbol = fut_symbol_base + str(nearest_Previousexpiry_price)
                combinedPreviousPrice = getCombinedCEPEData(samco,prevCloseSymbol,samco.EXCHANGE_NFO,"previousClose")
        
            ltpSymbol = fut_symbol_base + str(nearest_expiry_price)
            ltp = 0
            errorCheck = 0
            for i in chain:
                if(int(float(i["strikePrice"])) == nearest_expiry_price):
                    errorCheck+=1
                    ltp+=float(i["lastTradedPrice"])
            if(errorCheck != 2):
                print("===> There seems be an error with ltp(" + str(ltp) + ") from option chain. Temporarily substituting with quotes instead. Please cross-check given numbers. This is not supposed to happen. Report.")
                ltp = getCombinedCEPEData(samco,ltpSymbol,samco.EXCHANGE_NFO,"lastTradedPrice")

            min_range = nearest_expiry_price - count_range * __diffBwFutures__
            max_range = nearest_expiry_price + count_range * __diffBwFutures__
            ceSum = 0
            peSum = 0
            ceCount = 0
            peCount = 0
            skipCount = 0

            for i in chain:
                iStrikePrice = float(i["strikePrice"])
                if (min_range > iStrikePrice or iStrikePrice > max_range):
                    skipCount+=1
                    continue
                oic = int(float(i["openInterestChange"]))
                if ("CE" == i["optionType"]):
                    ceSum+=oic
                    ceCount+=1
                else:
                    peSum+=oic
                    peCount+=1
            if(skipCount > max(len(chain) - count_range * 2 + 1,0)):
                print("===>",skipCount,"options were skipped. This might be unintended. Please Report.")
            #print("Skip count="+str(skipCount))

            diff = peSum - ceSum
            trend_if = 1 if diff > 0 else 0
            trend = "up" if trend_if else "down"
            #lttStr = ltt.strftime('%H:%M:%S')
            row_dict["LTT"] = lttStr
            row_dict["SPOT"] = spot_price
            row_dict["ATMsk"] = nearest_expiry_price
            row_dict["PrCls"] = roundBy(combinedPreviousPrice)
            row_dict["LTP"] = roundBy(ltp)
            row_dict["CESum"] = formatINR(ceSum)
            row_dict["PESum"] = formatINR(peSum)
            row_dict["Diff"] = formatINR(diff)
            row_dict["NtDcy"] = roundBy(ltp - combinedPreviousPrice)
            row_dict["Trnd"] = trend
            
            if(displayCount):
                row_dict["CESum"] += str(ceCount)
                row_dict["PESum"] += str(peCount)

            currentRow = []
            for i in row_dict:
                currentRow.append(row_dict[i])
            # print("Current row of len",len(currentRow),":",currentRow)
            tableRows.append(currentRow)

            mini_df = pd.DataFrame([row_dict])
            if(clearScreenEveryDelay):
                os.system("cls")

            print(tabulate(mini_df, headers='keys', tablefmt='psql'))
            print(_datetime.now() , "Took around %s secs total" % (_datetime.now() - now).total_seconds())
            major_df = major_df.append(mini_df)

            if ((_datetime.now() - lastWriteTime).total_seconds() > writeLiveDataDelay):
                lastWriteTime = _datetime.now()
                # 2.2R: Appendability
                #major_df.to_csv(live_data_file_name)
                dataStr = ""
                if(not os.path.exists(live_data_file_name)):
                    for i in row_dict:
                        dataStr+=str(i) + ","
                    dataStr = dataStr[:-1] + "\n"
                while(lastWrittenN < len(tableRows)):
                    currentData = tableRows[lastWrittenN]
                    lastWrittenN+=1
                    currentDataStr = ""
                    for i in currentData:
                        x = '"' if type(i) != "string" else ''
                        currentDataStr+=x + str(i) + x + ","
                    if(len(currentData) > 0):
                        currentDataStr = currentDataStr[:-1]
                    dataStr+=currentDataStr + "\n"
                live_data_file = open(live_data_file_name,"a")
                live_data_file.write(dataStr)
                live_data_file.close()
            ithData+=1
            sleep(dataRequestDelay)
        else:
            print("New day, no more info")
            print(__safeExitMsg__)
            break
except KeyboardInterrupt:
    print(__safeExitMsg__)
