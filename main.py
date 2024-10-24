# web-debugger-backend

from fastapi import FastAPI, WebSocket, HTTPException
from database import test_collection
from pydantic import BaseModel
from bson import ObjectId
from typing import List
import pyvisa
from pyvisa import ResourceManager, VisaIOError 
import time

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

@app.post("/set_channel_voltage/{channel}/{voltage}")
def set_channel_voltage(channel: int, voltage: float):

    power_supply = connect_to_power_supply()
    chstring = 'INST CH' + str(channel)
    power_supply.write(chstring)
    vstring = 'VOLT ' + str(voltage)
    power_supply.write(vstring)
    power_supply.write('OUTP CH'+ str(channel)+',ON')
    time.sleep(sleep_timer)
    vol = power_supply.query('MEAS:VOLT? CH' + str(channel))

    return{f"Channel {str(channel)} Voltage set to {vol}"}

@app.post("/set_channel_current/{channel}/{current}")
def set_channel_current(channel:int, current:float):
    
    power_supply = connect_to_power_supply()
    chstring = 'INST CH' + str(channel)
    power_supply.write(chstring)
    cstring = 'CURR ' + str(current)
    power_supply.write(cstring)
    power_supply.write('OUTP CH' + str(channel) + ',ON')
    time.sleep(sleep_timer)
    curr = power_supply.query('MEAS:CURR? CH' + str(channel))

    return{f"Channel {str(channel)} Current set to {curr}"}

