# PCB_Debugger

README: Instruction Syntax

Setting Voltage Level on Power Supply:
SETV int<channel>, float<voltage> 
(Channel must be 1, 2, or 3, and voltage may be up to one decimal place)

Setting Current Level on Power Supply:
SETC int\<channel\>, float<current>
(Channel must be 1, 2, or 3, and current may be up to one decimal place)

Getting Voltage Level from Power Supply:
GETV int<channel>
(Channel must be 1, 2, or 3)

Getting Current Level from Power Supply:
GETC int<channel>
(Channel must be 1, 2, or 3)

Reading Voltage from Multimeter:
TSTV

Reading Current from Multimeter:
TSTC

Testing Continuity with Multimeter:
TSCO

Calculating Resistance based on Multimeter Readings:
TSTR

Probing Voltage:
PRBV int<minimum>, int<maximum>, float<step>

Probing Current:
PRBC int<minimum>, int<maximum>, float<step>
