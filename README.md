README: Instruction Syntax


# troubleshooting commands 
Setting Voltage Level on Power Supply:
SETV int<channel>, float<voltage>
(Channel must be 1, 2, or 3, and voltage may be up to one decimal place)

Setting Current Level on Power Supply:
SETC int<channel>, float<current>
(Channel must be 1, 2, or 3, and current may be up to one decimal place)

Getting Voltage Level from Power Supply:
GETV int<channel>
(Channel must be 1, 2, or 3)

Getting Current Level from Power Supply:
GETC int<channel>
(Channel must be 1, 2, or 3)

# measure v and c from multimeter



# getting global variables
# need to be set before everything else 
MAXC float<max current>
MAXV float<max voltage>

Testing Voltage:
TSTV int<channel>, float<voltage>, float<minimum>, float<maximum>
This command sets the voltage to <voltage>, measures the voltage after application, and returns a pass value if the measured voltage falls between the min and max. Returns fail otherwise.

Reading Current from Multimeter:
TSTC float<current>, float<minimum>, float<maximum>
This command sets the current to <current>, measures the current after application, and returns a pass value if the measured current falls between the min and max. Returns fail otherwise.

Testing Continuity with Multimeter:
TSCO
Measures whether the circuit is open or closed, and returns continuous or not continuous.

Calculating Resistance based on Multimeter Readings:
TSTR

Probing Voltage:
PRBV int<channel>, float<start>, float<end>, float<step>
This command probes voltage on <channel> starting from <start> and ending at <end> at step interval <step>.

Probing Current:
PRBC int<channel>, float<start>, float<end>, float<step>
This command probes current on <channel> starting from <start> and ending at <end> at step interval <step>.


SETV CH1, 4V


add board id to end of all commands (3 different boards) B1, B2, B3 along with channel 
add units to maxv and maxc

for each probe step check error (have range) 
pass or fail value for each 
two more values for probes 

pcbid, B1

