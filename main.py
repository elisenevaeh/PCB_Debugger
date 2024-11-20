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
from typing import List
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = {
    "http://localhost:3000",
    "http://localhost:8000"
}
# Allow all origins for development purposes (you can specify more restrictive origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins= origins,  # You can specify specific domains here, e.g., ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

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

def set_channel_voltage(channel: int, voltage: float):
    try:
        # Try to connect to the power supply
        power_supply = connect_to_power_supply()

        # Check if the connection is valid
        if not power_supply:
            raise HTTPException(status_code=500, detail="Failed to connect to power supply.")

        print(f"Power supply connected: {power_supply}")

        # Send the command to select the channel
        chstring = f'INST CH{channel}'
        print(f"Sending command to power supply: {chstring}")
        power_supply.write(chstring)

        # Send the voltage value
        vstring = f'VOLT {voltage}'
        print(f"Sending voltage value to power supply: {vstring}")
        power_supply.write(vstring)

        # Turn on the output for the channel
        outstring = f'OUTP CH{channel},ON'
        print(f"Sending output command to power supply: {outstring}")
        power_supply.write(outstring)

        # Return the success message
        return f"Channel {channel} Voltage set to {voltage}"

    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while setting the channel voltage.")


class MockPowerSupply:
    def write(self, command: str):
        print(f"Mock Power Supply received command: {command}")

#def connect_to_power_supply():
    # Return a mock power supply object for testing
    #return MockPowerSupply()

def set_channel_current(channel: int, current: float):
    try:
        print("Made it here")
        power_supply = connect_to_power_supply()

        # Check if the connection is valid
        if not power_supply:
            raise HTTPException(status_code=500, detail="Failed to connect to power supply.")

        print(f"Power supply connected: {power_supply}")

        # Send the command to set the channel
        chstring = f'INST CH{channel}'
        print(f"Sending command to power supply: {chstring}")
        power_supply.write(chstring)

        # Send the current value
        cstring = f'CURR {current}'
        print(f"Sending current value to power supply: {cstring}")
        power_supply.write(cstring)

        # Turn on the output for the channel
        outstring = f'OUTP CH{channel},ON'
        print(f"Sending output command to power supply: {outstring}")
        power_supply.write(outstring)

        print("made it here too")
        return f"Channel {channel} Current set to {current}"
    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while setting the channel current.")

# Similar adjustments to other endpoints to ensure they return a "message" field


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
        return float(voltage)
        #return {f"Measured Voltage: {voltage} V"}
    else:
        print("Multimeter connection not available.")

def measure_current():
    multimeter = connect_to_multimeter()
    if multimeter:
        multimeter.write(":MEAS:CURR:DC?")
        current = multimeter.read()
        return float(current)
        #return {f"Measured Current: {current} A"}
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

class CommandRequest(BaseModel):
    commands: List[str]

@app.post("/debugger")
async def process_commands(request: CommandRequest):
    responses = []

    for q in request.commands:
        # Handle SETV command
        if q[:4] == 'SETV':
            parts = q.strip().split(',')
            if len(parts) == 2:
                try:
                    # Extract the channel and voltage values by stripping extra spaces
                    channel = int(parts[0].strip().split()[1])  # Get channel after the 'TSTV' keyword
                    voltage = float(parts[1].strip())  # Get the voltage value after the comma
                    print(f"Received Channel: {channel}")
                    print(f"Received Voltage: {voltage}")

                    # Validate the channel
                    if channel < 1 or channel > 3:
                        raise HTTPException(status_code=400, detail="Channel must be 1, 2, or 3.")

                    # Call the function to set the channel voltage
                    response = set_channel_voltage(channel, voltage)
                    print(f"response: {response}")
                    responses.append(response)

                except ValueError:
                    responses.append("Error processing SETV command: Invalid input values. Channel and voltage must be valid numbers.")
            else:
                responses.append("Error processing SETV command: Invalid command format. Expected 'SETV <channel>, <voltage>'.")
        
            #responses.append(measure_voltage())
        # Handle SETC command
        elif q[:4] == 'SETC':
            print(f"Received query: {q}")
            parts = q.strip().split(',')
            if len(parts) == 2:
                try:
                    channel = int(parts[0].strip().split()[1])  # Get channel after the 'SETC' keyword
                    current = float(parts[1].strip())  # Get the current value after the comma
                    if channel < 1 or channel > 3:
                        raise HTTPException(status_code=400, detail="Channel must be 1, 2, or 3.")
                    response = set_channel_current(channel, current)
                    responses.append(response)
                except ValueError:
                    responses.append("Error processing SETC command: Invalid input values.")
            else:
                responses.append("Error processing SETC command: Invalid command format. Expected 'SETC <channel>, <current>'.")
        
        # Handle GETV command
        elif q[:4] == 'GETV':
            try:
                vals = re.findall(r'\d', q)[:1]
                ch = int(vals[0])
                if ch > 3 or ch < 1:
                    responses.append("Error processing GETV command: channel must be 1, 2, or 3")
                else:
                    vol = get_channel_voltage(ch)
                    responses.append(f"Voltage at channel {ch}: {vol}")
            except:
                responses.append("Error processing GETV command: Invalid channel.")

        # Handle GETC command
        elif q[:4] == 'GETC':
            vals = re.findall(r'\d', q)[:1]
            ch = int(vals[0])
            if ch > 3 or ch < 1:
                responses.append("Error processing GETC command: channel must be 1, 2, or 3")
            else:
                curr = get_channel_current(ch)
                responses.append(f"Current at channel {ch}: {curr}")

        # Handle TSTV command
        elif q[:4] == 'TSTV':
            print(f"Received query: {q}")
            # Split the command into parts
            parts = q.strip().split(',')
            if len(parts) == 3:
                try:
                    # Extract the channel and voltage values by stripping extra spaces
                    voltage = float(parts[0].strip().split()[1])  # get voltage 
                    minimum = float(parts[1].strip())  # get min after comma 
                    maximum = float(parts[2].strip()) # get max after comma 
                    print(f"Received Voltage: {voltage}")
                    print(f"Received Minimum: {minimum}")
                    print(f"Received Maximum: {maximum}")
                    
                    channel = 1
                    # validate the channel
                    if channel < 1 or channel > 3:
                        raise HTTPException(status_code=400, detail="Channel must be 1, 2, or 3.")

                    # Call the function to set the channel voltage
                    #response = set_channel_voltage(channel, voltage)
                    set_channel_voltage(channel, voltage)
                    time.sleep(1)
                    readV = measure_voltage()
                    
                    if (readV > maximum or readV < minimum):
                        passVal = False
                        response = {f"Measured voltage: {readV}V, Test Failed"}
                    else:
                        passVal = True
                        response = {f"Measured Voltage: {readV}V, Test Passed"}
                         
                    
                    print(f"response: {response}")
                    responses.append(response)

                except ValueError:
                    responses.append("Error processing TSTV command: Invalid input values.")
            else:
                responses.append("Error processing TSTV command: Invalid command format. Expected 'TSTV <voltage>, <minimum>, <maximum>'.")


        # Handle TSTC command
        elif q[:4] == 'TSTC':
            print(f"Received query: {q}")
            # Split the command into parts
            parts = q.strip().split(',')
            if len(parts) == 3:
                try:
                    # Extract the channel and voltage values by stripping extra spaces
                    current = float(parts[0].strip().split()[1])  # get voltage 
                    minimum = float(parts[1].strip())  # get min after comma 
                    maximum = float(parts[2].strip()) # get max after comma 
                    print(f"Received Voltage: {current}")
                    print(f"Received Minimum: {minimum}")
                    print(f"Received Maximum: {maximum}")
                    
                    channel = 1
                    # validate the channel
                    if channel < 1 or channel > 3:
                        raise HTTPException(status_code=400, detail="Channel must be 1, 2, or 3.")

                    # Call the function to set the channel voltage
                    #response = set_channel_voltage(channel, voltage)
                    set_channel_current(channel, current)
                    time.sleep(1)
                    readC = measure_current()
                    
                    if (readC > maximum or readC < minimum):
                        passVal = False
                        response = {f"Measured current: {readC}A, Test Failed"}
                    else:
                        passVal = True
                        response = {f"Measured current: {readC}A, Test Passed"}
                         
                    print(f"response: {response}")
                    responses.append(response)

                except ValueError:
                    responses.append("Error processing TSTV command: Invalid input values.")
            else:
                responses.append("Error processing TSTV command: Invalid command format. Expected 'TSTV <voltage>, <minimum>, <maximum>'.")


        # Handle TSCO command
        elif q[:4] == 'TSCO':
            responses.append(measure_continuity())

        # Handle TSTR command
        elif q[:4] == 'TSTR':
            multimeter = connect_to_multimeter()
            if multimeter:
                multimeter.write(":MEAS:RES?")
                resistance = multimeter.read()
                responses.append(f"Resistance: {resistance} Ohms")
            else:
                responses.append("Error processing TSTR command: multimeter not found")

        # Handle PRBV command
        elif q[:4] == 'PRBV':
            responses.append("PROBING VOLTAGE")

        # Handle PRBC command
        elif q[:4] == 'PRBC':
            responses.append("PROBING CURRENT")

        # If command not found
        else:
            responses.append(f"Error processing command '{q}': command not found")

    # Return all responses as a list of strings
    return {"responses": responses}


'''
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
maxVoltage = 3.3

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
                match = re.match(r"\s*SETV\s*(\d+)\s*,\s*([\d]+(\.\d{1})?)\s*$", q)
                
                if match:
                    # Extract the channel and voltage from the command
                    channel = int(match.group(1))  # Channel (should be an integer)
                    voltage = float(match.group(2))  # Voltage (should be a float)
                    if voltage > maxVoltage:
                        raise HTTPException(status_code=400, detail="Voltage may not exceed max voltage of board.")
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
            
            
            if(q[:4] == 'SETV'):  # setting voltage on power supply
            try:
                vals = re.findall(r'\d', q)[:2] # get first two digits in string
            except: 
                return{"error": {"need two integers in command"}}
            ch = vals[0]
            vol = vals[1]
            return set_channel_voltage(ch, vol)
'''
