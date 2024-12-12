# main.py
from fastapi import FastAPI, HTTPException, Depends, WebSocket
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from models import User, Login, Token, TokenData, CommandRequest  # Adjust the import based on your file structure
from fastapi.responses import JSONResponse  # Add this import for JSONResponse
from database import users, create_user, find_user_by_email, Hash, send_verification_email
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId
import pyvisa
from pyvisa import ResourceManager, VisaIOError
import time
from mail import mail, create_message
from itsdangerous import URLSafeTimedSerializer
import logging
from fastapi import BackgroundTasks
from utils import create_url_safe_token
from motor.motor_asyncio import AsyncIOMotorClient
from utils import serializer  # Ensure serializer is properly imported

# FastAPI initialization
app = FastAPI()

# CORS setup
origins = [
    "http://localhost:3000",
    "http://localhost:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],   # allows get, put, post, delete
    allow_headers=["*"],
)

# JWT Token setup
SECRET_KEY = "URgbP75FiM!YkZPF535UZPucsUR*G8*@zt"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Create JWT token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()  # Copy input data
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})  # Update expiration time
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

#token validation
@app.get("/verify/{token}")
async def verify_email(token: str):
    try:
        # Decode the token and get the email
        decoded_data = decode_url_safe_token(token)  # Assuming your decoding logic here
        email = decoded_data.get("email")

        # Ensure email exists in the database
        print(f"Finding user with email: {email}")
        user = await users.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # If the user is already verified, return an appropriate message
        if user.get("is_verified"):
            return JSONResponse(content={"message": "Email already verified!"})

        # Update the user to mark them as verified
        await users.update_one({"email": email}, {"$set": {"is_verified": True}})

        return JSONResponse(content={"message": "Email successfully verified!"})

    except Exception as e:
        logging.error(f"Error during email verification: {e}")
        raise HTTPException(status_code=400, detail="Invalid or expired token")

# OAuth2 scheme for token authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def decode_url_safe_token(token:str):
    try:
        token_data = serializer.loads(token)

        return token_data
    
    except Exception as e:
        logging.error(str(e))
        
# Registration endpoint
@app.post("/register")
async def register_user(request: User, bg_tasks: BackgroundTasks):
    return await create_user(request, bg_tasks)

# Login endpoint
@app.post("/login")
async def login(request: OAuth2PasswordRequestForm = Depends()):
    # Find user by email
    user = await find_user_by_email(request.username)
    if not user:
        raise HTTPException(status_code=404, detail="No user found with this email")

    # Check if the user's email is verified
    if not user.get("is_verified", False):  # Assuming 'is_verified' is a field in your user document
        raise HTTPException(status_code=400, detail="Email not verified. Please check your inbox to verify your email.")

    # Check if the password is correct
    if not Hash.verify(user["password"], request.password):
        raise HTTPException(status_code=403, detail="Incorrect email or password")

    # Create access token
    access_token = create_access_token(data={"sub": user["email"]})
    
    return {"access_token": access_token, "token_type": "bearer"}

sleep_timer = 1
maxVoltage = -1
maxCurrent = -1

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

def check_voltage_parameters(channel: int, voltage: float):
    if (voltage > maxVoltage):
        print("\nVoltage cannot be greater than the voltage rating of the circuit.")
        return 0
    else: 
        if (channel == 1): 
            if(voltage < 0 or voltage > 8): 
                print("\nVoltage must be set between 0V and 8V for channel 1.")
                return 0
            else: 
                return 1
        elif (channel == 2): 
            if(voltage < 0 or voltage > 30): 
                print("\nVoltage must be set between 0V and 30V for channel 2.")
                return 0
            else: 
                return 1
        elif (channel == 3): 
            if(voltage < -30 or voltage > 0): 
                print("\nVoltage must be set between -30V and 0V for channel 3.")
                return 0
            else: 
                return 1 

def check_current_parameters(channel: int, current: float):
    if (current > maxCurrent):
        print("\nCurrent cannot be greater than the current rating of the circuit.")
        return 0
    else: 
        if (channel == 1): 
            if(current < 0 or current > 5000): 
                print("\nCurrent must be set between 0A and 5A for channel 1.")
                return 0
            else: 
                return 1
        elif (channel == 2): 
            if(current < 0 or current > 2000): 
                print("\nCurrent must be set between 0A and 2A for channel 2.")
                return 0
            else: 
                return 1
        elif (channel == 3): 
            if(current < 0 or current > 2000): 
                print("\nCurrent must be set between 0A and 2A for channel 3.")
                return 0
            else: 
                return 1 

def set_channel_voltage(channel: int, voltage: float):
    power_supply = connect_to_power_supply()
    if power_supply:
        try:
            if(check_voltage_parameters(channel, voltage)):
                # set maximum current for channel 
                if(channel == 1): 
                    if (maxCurrent > 5000): 
                        power_supply.write('CURR 5')
                    else: 
                        cstring = f'CURR {maxCurrent/1000}'
                        power_supply.write(cstring)
                elif(channel == 2):
                    if (maxCurrent > 2000): 
                        power_supply.write('CURR 2')
                    else: 
                        cstring = f'CURR {maxCurrent/1000}'
                        power_supply.write(cstring)
                elif(channel == 3): 
                    if (maxCurrent > 2000): 
                        power_supply.write('CURR 2')
                    else: 
                        cstring = f'CURR {maxCurrent/1000}'
                        power_supply.write(cstring)
                
                # Set the voltage on the power supply
                chstring = f'INST CH{channel}'
                power_supply.write(chstring)
                vstring = f'VOLT {voltage}'
                power_supply.write(vstring)
                time.sleep(sleep_timer)

                # Enable output globally (if required by power supply)
                power_supply.write('OUTP ON')
                time.sleep(sleep_timer)

                # Measure and return the voltage set on the power supply
                vol = power_supply.query(f'MEAS:VOLT? CH{channel}')
                return {f"Channel {channel} Voltage set to {vol}"}
            else: 
                return
        except Exception as e:
            print("Error setting voltage:", e)
            return f"Error: {e}"
    else:
        return "Failed to connect to power supply"

class MockPowerSupply:
    def write(self, command: str):
        print(f"Mock Power Supply received command: {command}")

#def connect_to_power_supply():
    # Return a mock power supply object for testing
    #return MockPowerSupply()

def set_channel_current(channel: int, current: float):
    power_supply = connect_to_power_supply()
    if power_supply: 
        try:
            if(check_current_parameters(channel, current)): 
                # Set the current on the power supply
                chstring = f'INST CH{channel}'
                power_supply.write(chstring)
                cstring = f'CURR {current/1000}'
                power_supply.write(cstring)
                time.sleep(sleep_timer)
                # set maximum volts for channel 
                if(channel == 1): 
                    if (maxVoltage > 8): 
                        power_supply.write('VOLT 8')
                    else: 
                        vstring = f'VOLT {maxVoltage}'
                        power_supply.write(vstring)
                elif(channel == 2):
                    if (maxVoltage > 8): 
                        power_supply.write('VOLT 30')
                    else: 
                        vstring = f'VOLT {maxVoltage}'
                        power_supply.write(vstring)
                elif(channel == 3): 
                    if (maxVoltage < -30): 
                        power_supply.write('VOLT 30')
                    else: 
                        vstring = f'VOLT {maxVoltage}'
                        power_supply.write(vstring)

                # Enable output globally (if required by power supply)
                power_supply.write('OUTP ON')
                time.sleep(sleep_timer)
                # Measure and return the voltage set on the power suppl
                curr = power_supply.query(f'MEAS:CURR? CH{channel}')
                return {f"Channel {channel} Current set to {current}mA"}
            else: 
                return
        except Exception as e:
            print("Error setting current:", e)
            return f"Error: {e}"
    else: 
        return "Failed to connect to power supply"


def get_channel_voltage(channel:int):
    print ("made it here")
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
        voltageFloat = float(voltage)
        print(f"Measured Voltage: {round(voltageFloat, 5)}V")
        return voltageFloat
    else:
        print("Multimeter connection not available.")

def measure_current():
    multimeter = connect_to_multimeter()
    if multimeter: 
        multimeter.write(":MEAS:CURR:DC?")
        current = multimeter.read()
        currentFloat = float(current)
        currentFloat = currentFloat*1000 # set to mA
        print(f"Measured Current: {round(currentFloat, 5)}mA")
        return currentFloat
    else:
        print("Multimeter connection not available.")

def test_continuity():
    multimeter = connect_to_multimeter()
    if multimeter: 
        # Set to continuity mode or measure resistance
        multimeter.write(":MEAS:CONT?")
        continuity = multimeter.read()
        if continuity.strip() == '1':
            return "Continuous, close circuit"
        else:
            return "Not continous, open circuit"
    else:
        print("Multimeter connection not available.")

def probe_voltage(channel: int, startV: float, endV: float, stepV: float): 

    # Check if the voltage parameters are valid for both startV and endV
    if not (check_voltage_parameters(channel, startV) and check_voltage_parameters(channel, endV)):
        return "Invalid voltage parameters."

    probeV = startV
    while probeV <= endV:  # Loop until we reach endV
        set_channel_voltage(channel, probeV)
        print(f"Probing voltage at {probeV}V")  # Optionally log the voltage
        time.sleep(sleep_timer); 
        measure_voltage(); 
        probeV += stepV  # Increment the voltage by stepV
        
    # Ensure the last voltage is set to endV if it goes beyond
    set_channel_voltage(channel, endV)
    print(f"Probing voltage at {endV}V")  # Optionally log the voltage
    time.sleep(sleep_timer); 
    measure_voltage(); 
    print("\nEnd of Voltage Probing")


def probe_current(channel: int, startC: float, endC: float, stepC: float): 
    # Check if the current parameters are valid for both startCand endC
    if not (check_current_parameters(channel, startC) and check_current_parameters(channel, endC)):
        return "Invalid Current parameters."

    probeC = startC
    while probeC <= endC:  # Loop until we reach endV
        set_channel_current(channel, probeC)
        print(f"Probing current at {probeC}mA")  # Optionally log the current
        time.sleep(sleep_timer) 
        measure_current()
        probeC += stepC  # Increment the current by stepV
        
    # Ensure the last current is set to endV if it goes beyond
    set_channel_current(channel, endC)
    print(f"Probing Current at {endC}mA")  # Optionally log the current
    time.sleep(sleep_timer) 
    measure_current()
    print("\nEnd of Current Probing")

@app.post("/dashboard")
async def process_commands(request: CommandRequest):
    responses = []

    for q in request.commands:
        # Handle SETV command
        if q[:4] == 'MAXV':
            # get max voltage rating for board 
            parts = q.strip().split(' ')
            if len(parts) == 2:
                try: 
                    global maxVoltage
                    maxVoltage = float(parts[1])

                except ValueError:
                    responses.append("Error processing MAXV command: invalid input")
            
            responses.append(f"Voltage Rating: {maxVoltage}")

        elif q[:4] == 'MAXC':
            # get max current rating for board
            parts = q.strip().split(' ')
            if len(parts) == 2:
                try:
                    global maxCurrent
                    maxCurrent = float(parts[1])

                except ValueError:
                    responses.append("Error processing MAXC command: invalid input")
            
            responses.append(f"Current Rating: {maxCurrent}")
        elif q[:4] == 'SETV':
            if maxCurrent == -1 or maxVoltage == -1:
                responses.append("use MAXV to set max voltage and MAXC to set max current")
            else:
                parts = q.strip().split(',')
                print(f"Parts[0]:  {parts[0]}, Parts[1]: {parts[1]}")
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
            if maxCurrent == -1 or maxVoltage == -1:
                responses.append("use MAXV to set max voltage and MAXC to set max current")
            else: 
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
            if maxCurrent == -1 or maxVoltage == -1:
                responses.append("use MAXV to set max voltage and MAXC to set max current")
            else:
                parts = q.strip().split(' ')
                print (f"part1: {parts[0]}, ch: {parts[1]}, len: {len(parts)}")
                try:
                    print ("making it inside try")
                    #vals = re.findall(r'\d', q)[:1]
                    if len(parts) == 2:
                        print ("making it inside if")
                        ch = int(parts[1].strip())
                        print (f"ch: {ch}")
                        if ch > 3 or ch < 1:
                            responses.append("Error processing GETV command: channel must be 1, 2, or 3")
                        else:
                            vol = get_channel_voltage(ch)
                            responses.append(f"Voltage at channel {ch}: {vol}")
                except:
                    responses.append("Error processing GETV command: Invalid channel.")

        # Handle GETC command
        elif q[:4] == 'GETC':
            if maxCurrent == -1 or maxVoltage == -1:
                responses.append("use MAXV to set max voltage and MAXC to set max current")
            else: 
                parts = q.strip().split(' ')
                print (f"part1: {parts[0]}, ch: {parts[1]}, len: {len(parts)}")
                try:
                    print ("making it inside try")
                    #vals = re.findall(r'\d', q)[:1]
                    if len(parts) == 2:
                        print ("making it inside if")
                        ch = int(parts[1].strip())
                        print (f"ch: {ch}")
                        if ch > 3 or ch < 1:
                            responses.append("Error processing GETV command: channel must be 1, 2, or 3")
                        else:
                            curr = get_channel_current(ch)
                            responses.append(f"Current at channel {ch}: {curr}")
                except:
                    responses.append("Error processing GETV command: Invalid channel.")
            

        # Handle TSTV command
        elif q[:4] == 'TSTV':
            print(f"Received query: {q}")
            # Split the command into parts
            if maxVoltage == -1 or maxCurrent == -1:
                responses.append("use MAXV to set max voltage and MAXC to set max current")
            
            else:
                
                parts = q.strip().split(',')
                if len(parts) == 4:
                    try:
                        # Extract the channel and voltage values by stripping extra spaces
                        channel = int(parts[0].strip().split()[1])
                        voltage = float(parts[1].strip())  # get voltage 
                        minimum = float(parts[2].strip())  # get min after comma 
                        maximum = float(parts[3].strip()) # get max after comma 
                        print(f"Received Voltage: {voltage}")
                        print(f"Received Minimum: {minimum}")
                        print(f"Received Maximum: {maximum}")
                        
                        #channel = 1
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
            if maxCurrent == -1 or maxVoltage == -1:
                responses.append("use MAXV to set max voltage and MAXC to set max current")
            else:

                parts = q.strip().split(',')
                if len(parts) == 4:
                    try:
                        # Extract the channel and voltage values by stripping extra spaces
                        channel = int(parts[0].strip().split()[1])
                        current = float(parts[1].strip())  # get voltage 
                        minimum = float(parts[2].strip())  # get min after comma 
                        maximum = float(parts[3].strip()) # get max after comma 
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
                            response = {f"Measured current: {readC}mA, Test Failed"}
                        else:
                            passVal = True
                            response = {f"Measured current: {readC}mA, Test Passed"}
                            
                        print(f"response: {response}")
                        responses.append(response)

                    except ValueError:
                        responses.append("Error processing TSTV command: Invalid input values.")
                else:
                    responses.append("Error processing TSTV command: Invalid command format. Expected 'TSTV <voltage>, <minimum>, <maximum>'.")


        # Handle TSCO command
        elif q[:4] == 'TSCO':
            if maxCurrent == -1 or maxVoltage == -1:
                responses.append("use MAXV to set max voltage and MAXC to set max current")
            else:
                responses.append("Measuring continuity") # for testing 
                responses.append(test_continuity())

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
            if maxCurrent == -1 or maxVoltage == -1:
                responses.append("use MAXV to set max voltage and MAXC to set max current")
            else:
                print(f"Received query: {q}")
                # Split the command into parts
                parts = q.strip().split(',')
                if len(parts) == 4:
                    try:
                        
                        channel = int(parts[0].strip().split()[1])
                        start = float(parts[1].strip())  # get start 
                        end = float(parts[2].strip())  # get end after comma 
                        step = float(parts[3].strip()) # get step after comma 
                        print(f"Received Start: {start}")
                        print(f"Received End: {end}")
                        print(f"Received Step: {step}")
                        
                        #channel = 1
                        # validate the channel
                        if channel < 1 or channel > 3:
                            raise HTTPException(status_code=400, detail="Channel must be 1, 2, or 3.")

                        probe_voltage(channel, start, end, step)
                        #responses.append(response)

                    except ValueError:
                        responses.append("Error processing PRBV command: Invalid input format")

                responses.append("PROBED VOLTAGE")

        # Handle PRBC command
        elif q[:4] == 'PRBC':
            if maxCurrent == -1 or maxVoltage == -1:
                responses.append("use MAXV to set max voltage and MAXC to set max current")
            else:
                print(f"Received query: {q}")
                # Split the command into parts
                parts = q.strip().split(',')
                if len(parts) == 4:
                    try:
                        # Extract the channel and voltage values by stripping extra spaces
                        channel = int(parts[0].strip().split()[1])
                        start = float(parts[1].strip())  # get start 
                        end = float(parts[2].strip())  # get end after comma 
                        step = float(parts[3].strip()) # get step after comma 
                        print(f"Received Start: {start}")
                        print(f"Received End: {end}")
                        print(f"Received Step: {step}")
                        
                        #channel = 1
                        # validate the channel
                        if channel < 1 or channel > 3:
                            raise HTTPException(status_code=400, detail="Channel must be 1, 2, or 3.")

                        probe_current(channel, start, end, step)

                    except ValueError:
                        responses.append("Error processing PRBC command: Invalid input format")


                responses.append("PROBED CURRENT")

        # If command not found
        else:
            responses.append(f"Error processing command '{q}': command not found")

    # Return all responses as a list of strings
    return {"responses": responses}

