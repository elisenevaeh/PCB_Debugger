# PCB_Debugger

README: Instruction Syntax

Setting Voltage Level on Power Supply: <br>
SETV int\<channel\>, float\<voltage\> <br>
(Channel must be 1, 2, or 3, and voltage may be up to one decimal place) <br>
<br>
Setting Current Level on Power Supply: <br>
SETC int\<channel\>, float\<current\> <br>
(Channel must be 1, 2, or 3, and current may be up to one decimal place) <br>
<br>
Getting Voltage Level from Power Supply: <br>
GETV int\<channel\> <br>
(Channel must be 1, 2, or 3) <br>
<br>
Getting Current Level from Power Supply: <br>
GETC int\<channel\> <br>
(Channel must be 1, 2, or 3) <br>
<br>
Reading Voltage from Multimeter: <br>
TSTV <br>
<br>
Reading Current from Multimeter: <br>
TSTC <br>
<br>
Testing Continuity with Multimeter: <br>
TSCO <br>
<br>
Calculating Resistance based on Multimeter Readings: <br>
TSTR <br>
<br>
Probing Voltage: <br>
PRBV int\<minimum\>, int\<maximum\>, float\<step\> <br>
<br>
Probing Current: <br>
PRBC int\<minimum\>, int\<maximum\>, float\<step\> <br>
<br>
