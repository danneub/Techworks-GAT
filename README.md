Neuburger's info about the GAT trainer software    12/4/2025

in github website  generate the Presonal Access Token
( so that the PI can access/modify the repository )

sign on to Github - danneub (pw - A*01!)
project Techworks-GAT
select user icon in upper right of page
> settings
> Developer Settings > Generate new token (classic)
> check - classic -> scopes:repo
save the token value generated

-----------------------------------------------
on the PI

log in

git config --global user.email "dhneuburger@gmail.com"
git config --global user.name "danneub"
mkdir /homa/pi/GAT
cd /home/pi/GAT
git clone https://github.com/danneub/Techworks-GAT.git
cd GAT
git remote set-url origin https://danneub:[token]@github.com/danneub/Techworks-GAT.git
- don't type in the [] characters


This disk has several folders:
 - /MOD-EMUP   - prom burner software. I'm not sure if this includes the version on the PC at techworks but might be useful for offline study of the tool
 - /photos - some photos of the Motorola cards in the VME bin
 - /Quelo68K_2025 - source code for the GAT along with the Quelo 68K assembler/linker tools and tool documentation
 - /manuals  - some manuals for the hardware as well as the Hazeltine 1500 terminal (which is used by the debug facility)



Basic info on the trainer:
The trainer uses a VME bus based computer system. There are several custom Link cards, which I don't know much about yet. There are three Motorola cards. The MVME-110 is a 68000 processor based single board computer (SBC). The MVME-201 proved additional RAM for the SBC. The MVME-400 dual serial card provides an RS-232 output which can be connected to software configured to emulate a Hazeltine-1500 terminal.

MVME-110 runs two pieces of software: the sim program, VMEbug 2.0  

 - The sim software was written by Link and is entirely in 68K assembly code.
 - VMEbug came from Motorola and might have been modified by link. I currently don't have source code for this, but there are some versions of
   it out on the internet.
 - Both pieces of software are burned into EEPROMS on the MVME-110. There is a PC in the lab with a  "Modular Circuit Technology" MOD-EMUP programmer attached to it. This could be used to burn new EEPROMS. The MOD-EMUP software is also on that PC.


BUILDING THE SIM LOAD:
 - there are probably just a few steps involved with building the sim load
   1. compile the source code into a Motorola S-Record format file (.HEX)
   2. transfer the HEX file to the pc with the prom burner
   3. burn the sim load into intel D2764-2 EEPROM chips
   4. replace the 4 EEPROM chips on the MVME-110 card


  Step 1. compiling the code
  a. install DOSBox on a windows(10/11) pc.  I used version 0.74-3 on a Windows 11 Home system.
  b. load the CD with all the GAT source code where your pc can see it
  c. start DOSBox
  d. mount the folder containing the GAT source code to DOSBox  example: "mount d c:/users/dhneu/documents/techworks/quelo86k_2025"
     This will mount the GAT source and build tools to the "D" drive of DOSBox
  e. Change to the "D:" drive on DOSBox   "D:"   ,  verify your in the right place by displaying the contents of the directory "dir"
  f. kick off the source build "build.bat"  This will take a few minutes to complete.
  g. when it's complete there should be a file with the current date/time named QLOAD1.HEX.  This is the Motorola SRecord file



GAT SIM debugging:
  The GAT software has a built in debug facility. If the second serial port of the MVME-400 is connected to a PC running a Hazeltine terminal emulation, the debugger should be up and running. If the debugger doesn't understand your input, it should display a "????" prompt. It does require upper case.
Supported commands:
  PS - put symbol     PS,SYMBOL  or PS,<ADDRESS>[,<LEN>][,<TYPE>]    LEN=B|W|L   TYPE= H|D|F|Snn
      examples: PS,VISON     PS,NGLAT

  MM - modify memory  format same as PS command
      example:  MM,VISON     enter a 1 and then enter a blank

  S -  same as MM command   input formats for data    $nn = HEX    &nn = decimal
  CL - clear screen and remove symbols
  RE - reset load
  TE - module timer enable
  TD - module timer disable
  TR - module timer reset
  DC - desk calculator (not sure what this does- it might convert a number to binary)
  ME - module enable command     ME,<MODULE>
  MD - module disable command    same format as ME
  MI - module information        same format as ME


VMEBug

  If an RS-232 cable is connected from the MVME110 to a terminal emulator (not 
Hazel), VMEBug and the SIM can display information on the screen.  
  When the SIM normally boots up it will display 5 hex values on the screen.  (SSTACK, USTACK, LPOOL, DEBUG1, HEAP). 

  To use VMEBug when the SIM is up and running, press the ABORT button on the MVME110. You should then see a VMEBUG 2.0> prompt on the terminal.
  From here you can type VMEBug command. A list of command is in the file manuals/vmebug_commands.pdf.
  examples:
     MD 0F046FC    - displays the data in memory location 0F046FC
     T              - steps one instruction and dumps out the registers
     GO            - lets the software run free again
     
