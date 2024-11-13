# web debugger backend connected to power supply and multimeter 

from fastapi import FastAPI, WebSocket, HTTPException
#from database import test_collection
from pydantic import BaseModel
from bson import ObjectId
from typing import List
import pyvisa
from pyvisa import ResourceManager, VisaIOError 
import time
from typing import Union
import re 

app = FastAPI()

sleep_timer = 1

# WebSocket Endpoint for real-time communication
@app.websocket("/ws/test/{test_id}")
async def websocket_endpoint(websocket: WebSocket, test_id: str):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Test {test_id}: {data}")

def connect_to_power_supply():
    rm = pyvisa.ResourceManager()
    try:
        power_supply = rm.open_resource('USB0::0x1AB1::0x0E11::DP8A253700506::INSTR')  # Replace with actual VISA address
        return power_supply
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/SETV/{channel}/{voltage}")
def set_channel_voltage(channel: int, voltage: float):

    power_supply = connect_to_power_supply()
    chstring = 'INST CH' + str(channel)
    power_supply.write(chstring)
    vstring = 'VOLT ' + str(voltage)
    power_supply.write(vstring)
    power_supply.write('OUTP CH'+ str(channel)+',ON')

    return{f"Channel {str(channel)} Voltage set to {voltage}"}

@app.post("/set_channel_current/{channel}/{current}")
def set_channel_current(channel:int, current:float):
    
    power_supply = connect_to_power_supply()
    chstring = 'INST CH' + str(channel)
    power_supply.write(chstring)
    cstring = 'CURR ' + str(current)
    power_supply.write(cstring)
    power_supply.write('OUTP CH' + str(channel) + ',ON')

    return{f"Channel {str(channel)} Current set to {current}"}

def get_channel_voltage(channel:int):
    power_supply = connect_to_power_supply()
    vol = power_supply.query('MEAS:VOLT? CH' + str(channel))
    return vol

def get_channel_current(channel:int):
    power_supply = connect_to_power_supply()
    curr = power_supply.query('MEAS:CURR? CH' + str(channel))
    return curr

def connect_to_multimeter(): 
    rm = pyvisa.ResourceManager()
    try: 
        multimeter = rm.open_resource('USB0::62700::4614::SDM35HBQ7R1319::0::INSTR')
        return multimeter
    except pyvisa.VisaIOError as e: 
        print("Connection error:", e)
        raise HTTPException(status_code=500, detail=str(e))

def measure_voltage():
    multimeter = connect_to_multimeter()
    if multimeter: 
        multimeter.write(":MEAS:VOLT:DC?")
        voltage = multimeter.read()
        return {f"Measured Voltage: {voltage} V"}
    else:
        print("Multimeter connection not available.")

def measure_current():
    multimeter = connect_to_multimeter()
    if multimeter: 
        multimeter.write(":MEAS:CURR:DC?")
        current = multimeter.read()
        return {f"Measured Current: {current} A"}
    else:
        print("Multimeter connection not available.")

def measure_continuity():
    multimeter = connect_to_multimeter()
    if multimeter: 
        multimeter.write(":MEAS:CONT?")
        continuity = multimeter.read()
        
        # Interpret the result if necessary
        if continuity.strip() == "1":  # Adjust based on your multimeter's response
            return {"Continuity": "Closed (Continuity detected)"}
        else:
            return {"Continuity": "Open (No continuity)"}
    else:
        print("Multimeter connection not available.")

@app.get("/command/")
async def read_items(q: Union[str, None] = None):
    if q:
        if q[:4] == 'SETV':
            try:
                # Use a regex to match the command format "SETV <channel>, <voltage>"
                match = re.match(r"SETV\s*(\d+)\s*,\s*([\d]+(\.\d{1})?)$", q)
                
                if match:
                    # Extract the channel and voltage from the command
                    channel = int(match.group(1))  # Channel (should be an integer)
                    voltage = float(match.group(2))  # Voltage (should be a float)

                    # Error check: Ensure the channel is within the expected range
                    if channel < 1 or channel > 3:
                        raise HTTPException(status_code=400, detail="Channel must be 1, 2, or 3.")
                    
                    # Call the function to set the voltage on the power supply
                    return set_channel_voltage(channel, voltage)
                
                else:
                    raise HTTPException(status_code=400, detail="Invalid command format. Expected 'SETV <channel>, <voltage>'.")

            except ValueError as e:
                # This catches if the conversion of channel or voltage fails
                raise HTTPException(status_code=400, detail="Invalid input values. Channel and voltage must be valid numbers.")
 
        elif(q[:4] == 'SETC'):  # setting current on power supply 
            try:
                # Use a regex to match the command format "SETV <channel>, <voltage>"
                match = re.match(r"SETC\s*(\d+)\s*,\s*([\d]+(\.\d{1})?)$", q)
                
                if match:
                    # Extract the channel and voltage from the command
                    channel = int(match.group(1))  # Channel (should be an integer)
                    current = float(match.group(2))  # Voltage (should be a float)

                    # Error check: Ensure the channel is within the expected range
                    if channel < 1 or channel > 3:
                        raise HTTPException(status_code=400, detail="Channel must be 1, 2, or 3.")
                    
                    # Call the function to set the voltage on the power supply
                    return set_channel_current(channel, current)
                
                else:
                    raise HTTPException(status_code=400, detail="Invalid command format. Expected 'SETC <channel>, <current>'.")

            except ValueError as e:
                # This catches if the conversion of channel or voltage fails
                raise HTTPException(status_code=400, detail="Invalid input values. Channel and current must be valid numbers.")
 

        elif(q[:4] == 'GETV'):  # used to read voltage from POWER SUPPLY 
            try:
                vals = re.findall(r'\d', q)[:1] # get channel number 
            except: 
                return {"error": "need channel number"}
            ch = int(vals[0])
            if ch > 3 or ch < 1:
                return {"error": "channel must be 1, 2, or 3"}
            vol = get_channel_voltage(ch)
            return {f"Voltage at channel {str(ch)}: {str(vol)}"}
        
        elif(q[:4] == 'GETC'):  # used to read current from POWER SUPPLY 
            vals = re.findall(r'\d', q)[:1] # get channel number 
            ch = int(vals[0])
            if ch > 3 or ch < 1:
                return {"error": "channel must be 1, 2, or 3"}
            curr = get_channel_current(ch)
            return {f"Voltage at channel {str(ch)}: {str(curr)}"}

        elif(q[:4] == 'TSTV'): # used to test voltage with MULTIMETER
            return measure_voltage()

        elif(q[:4] == 'TSTC'):  # used to test current with MULTIMETER
            return measure_current()

        elif(q[:4] == 'TSCO'): # used to test continuity with MULTIMETER 
            return measure_continuity()
        # need probing functions 

        elif(q[:4] == 'TSTR'):  # used to calculate resistance 
            multimeter = connect_to_multimeter()
            if multimeter: 
                multimeter.write(":MEAS:CURR:DC?")
                current = multimeter.read() 

                multimeter.write(":MEAS:VOLT:DC?")
                voltage = multimeter.read()

                resistance = float(voltage) / float(current)

                return {f"Resistance: {resistance} Ohms"}

            else:
                print("multimeter not found")
                
        elif(q[:4] == 'PRBV'):  # probing voltage - params: min, max, step
            return {"PROBING VOLTAGE"} 
        
        elif(q[:4] == 'PRBC'):  # probing current - params: min, max, step 
            return {"PROBING CURRENT"} 

        else:   # for command not found case 
            return {"error": "command not found"} 
            
            
            '''if(q[:4] == 'SETV'):  # setting voltage on power supply
            try:
                vals = re.findall(r'\d', q)[:2] # get first two digits in string
            except: 
                return{"error": {"need two integers in command"}}
            ch = vals[0]
            vol = vals[1]
            return set_channel_voltage(ch, vol)
'''
