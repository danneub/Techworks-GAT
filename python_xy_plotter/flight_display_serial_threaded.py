import queue
import threading
from multiprocessing import Process, Queue
import serial
import time
import struct 
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as patches
import matplotlib.transforms as transforms
from matplotlib.widgets import TextBox
import csv
import pandas as pd

import numpy as np
import math

# Use the 'TkAgg' backend for better interactive compatibility
# You might need to install: pip install tk
import matplotlib
matplotlib.use('TkAgg')

# --- Configuration ---
FIG_SIZE = (10, 8)
X_LIMITS = (-25000, 25000)
Y_LIMITS = (-25000, 25000)
MARKER_SIZE=1000
# --- Initial Data Storage ---
# Store the history of flight coordinates
flight_path_x = []
flight_path_y = []
current_heading = 0 # Initial heading in degrees

# --- Static Map Data (Runways and Navaids) ---

# Airport Runways (as lines: [x_start, y_start, heading_deg, length])
runway_data = [
    [10000, 10000, -180, 5000, 'Linkville'],
    [0, 0, -180, 5000, 'MOUNTAIN DALE'] ]

# Navaids (as polygons: [[x1, y1], [x2, y2], ...])
navaids = [
    # A simple triangle navaid
    [[-80, -10], [-70, -10], [-75, -20], [-80, -10]],
    # A simple square navaid
    [[70, 10], [80, 10], [80, 20], [70, 20], [70, 10]],
    [[.7,.1], [.8,.1], [.8,.2],[.7,.2],[.7,.1]]
]

# potential replacement for the triangle airship, but
# polgons are harder to use than RegularPolygons, for me
# Cessna 172 Top-down Silhouette Coordinates (normalized)
# Vertices defined as [x, y] points
cessna_coords = np.array([
    [0.0, 1.0],   # 1. Nose Tip
    [1.0, 2.0],   # 2. Right Cowling
    [2.0, 2.50],  # 3. Right Windshield
    [4.0, 2.5],  # 4. Right Wing Root (front)
    [4.0, 8.0],   # 5. Right Wing Tip (forward)
    [5.0, 8.5],  # 6. Right Wing Tip (outer)
    [5.5, 7.5], # 7. Right Wing Tip (trailing)
    [4.5, 2.0],  # 8. Right Wing Root (back)
    [7., 1.5],  # 9. Right Fuselage/Tail
    [8., 3.0],   # 10. Right Horizontal Tail
    [9.0, 3.0],   # 11. Right Horizontal Tail Tip
    [9.5, 0.0],  # 12. Rear Tail Tip (Right)
    [9.5, -0.0], # 13. Rear Tail Tip (Left) - Centerline
    [9.0, -3.0],  # 14. Left Horizontal Tail Tip
    [8.0, -3.0],  # 15. Left Horizontal Tail
    [7., -1.5], # 16. Left Fuselage/Tail
    [4.5, -2.0], # 17. Left Wing Root (back)
    [5.5, -7.5],# 18. Left Wing Tip (trailing)
    [5.0, -8.5], # 19. Left Wing Tip (outer)
    [4.0, -8.0],  # 20. Left Wing Tip (forward)
    [4.0, -2.5], # 21. Left Wing Root (front)
    [2.0, -2.5], # 22. Left Windshield
    [1.0, -2.0],  # 23. Left Cowling
    [0.0, -1.0]   # 24. Nose Tip (back to start)
])
cessna_rotation_center = (0,0)

# data queue to hold the latest data
data_queue = queue.Queue(maxsize = 2)
stop_event = threading.Event()


file_name ='flight_data_1_16_2026.txt'
file_name ='1_23_2026.log'
file_open = False

def rotate_polygon(vertices, angle_rad, rotation_point):
    """Rotates polygon vertices around a given point."""
    rotated_vertices = []
    for x, y in vertices:
        # Translate point to origin
        tx, ty = x - rotation_point[0], y - rotation_point[1]
        # Rotate
        new_x = tx * np.cos(angle_rad) - ty * np.sin(angle_rad)
        new_y = tx * np.sin(angle_rad) + ty * np.cos(angle_rad)
        # Translate back
        rotated_vertices.append((new_x + rotation_point[0], new_y + rotation_point[1]))
    return np.array(rotated_vertices)

def generate_runway(start_point, angle_degrees, length ):
    """
    Generates a line based on a starting point, length, and angle.
    """
    x1, y1 = start_point
    # Convert angle to radians
    angle_rad = math.radians(angle_degrees-90)
    
    # Calculate end point
    x2 = x1 + length * math.cos(angle_rad)
    y2 = y1 + length * math.sin(angle_rad)
    
    print("gen_runway:",x1,y1,length,angle_degrees)

    return (x1, y1), (x2, y2)

def initialize_plot():
    """Sets up the initial figure, axes, and static map elements."""
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.set_xlim(X_LIMITS)
    ax.set_ylim(Y_LIMITS)
    ax.set_xlabel("X Coordinate")
    ax.set_ylabel("Y Coordinate")
    ax.set_title("Live Aircraft Tracking Simulation")
    ax.grid(True)
    
    # Add static runways
    for rwy in runway_data:
        start, end = generate_runway( [rwy[0],rwy[1]],rwy[2],rwy[3])
        ax.plot([start[0],end[0]],[start[1],end[1]], color='gray', linestyle='-', linewidth=5)
        ax.annotate(rwy[4], xy=((start[0]+end[0])/2+5,(start[1]+end[1])/2+5))
        print("runway:",start[0],end[0],start[1],end[1])


    # Add static navaids
    for nav in navaids:
        polygon = patches.Polygon(nav, closed=True, edgecolor='blue', facecolor='lightblue')      
        # offset_transforms = transforms.blended_transform_factory(ax.transData,ax.transAxes,a) 
        # polygon = patches.Polygon(nav, closed=True, edgecolor='blue', facecolor='lightblue',transform=offset_transforms)
        ax.add_patch(polygon)
    
    # VOR 
    ax.plot([-2500,-2500],[2500,2500],fillstyle='full',marker='H',markeredgecolor='blue',color='white',markersize=15)
    ax.plot([-2500,-2500],[2500,2500],fillstyle='full',marker='.',markeredgecolor='blue',color='blue',markersize=5)

    # VOR/DME 
    ax.plot([0,0],[0,0],fillstyle='full',marker='s',markeredgecolor='blue',markersize=15)
    ax.plot([0,0],[0,0],fillstyle='full',marker='H',markeredgecolor='blue',color='white',markersize=15)
    ax.plot([0,0],[0,0],fillstyle='full',marker='.',markeredgecolor='blue',color='blue',markersize=5)
    ilsfreq = 108.3
    ndbfreq = 201
    textstr = '\n'.join((
      r'ILS %.1f' % (ilsfreq, ),
      r'NDB %.1f' % (ndbfreq, )))
    props = dict(boxstyle='round', facecolor = 'wheat', alpha = 0.5)
    ax.text( 1000, 1000, textstr, fontsize=10, verticalalignment='top', bbox=props)
 
    # Initialize the flight path line and the aircraft marker
    line, = ax.plot([], [], color='red', linestyle='-', linewidth=1.5)
    
    # create parameters display box
    axbox = fig.add_axes([0.7,0.85,0.2,0.1])
    text_box = TextBox(axbox, '',initial='ALT: 0.00')
    text_box.text_disp.set_fontsize(20)
    
    # The aircraft is represented by a dynamically updated triangle patch
    aircraft_marker = patches.RegularPolygon((0, 0), numVertices=3, radius=MARKER_SIZE, 
                                             orientation=math.radians(0), color='green')

     #aircraft_marker = patches.Polygon(cessna_coords, closed=True, facecolor='green', edgecolor='black')

    ax.add_patch(aircraft_marker)
    ax.set_aspect('equal', adjustable='box')

    return fig, ax, line, aircraft_marker, text_box

def scale_aircraft_marker():
    # get the current x/y limits, we may have zoomed in/out
    bottom_ylim, top_ylim = ax.get_ylim()
    left_xlim, right_xlim = ax.get_xlim()
    scale = (top_ylim - bottom_ylim)/(X_LIMITS[1] - X_LIMITS[0])

    return scale

## ----------------------------------------------  make up data -------
def generate_figure_eight(data_queue):
    """Generates coordinates and heading for a figure-eight flight path simulation."""
    t = 0
    while not stop_event.is_set():
        t = t + 1
        # Parameters for the figure-eight
        a = 5000 # Radius of loops
        b = 0.0005 # Speed/frequency
        
        x = a * math.sin(b * t)
        y = a * math.sin(b * t) * math.cos(b * t)
        
        # Calculate heading (direction of movement)
        # Numerical derivative for approximation of the tangent vector
        dt = 0.1
        x_next = a * math.sin(b * (t + dt))
        y_next = a * math.sin(b * (t + dt)) * math.cos(b * (t + dt))
        
        dx = x_next - x
        dy = y_next - y
        
        # Heading in degrees, adjusted for Matplotlib's rotation angle (clockwise from +X)
        # Heading is typically measured clockwise from North (+Y axis).
        # math.atan2 gives radians CCW from +X.
        # Conversion: heading = 90 - degrees(atan2(dy, dx))
        heading_rad = math.atan2(dy, dx)
        heading_deg = (math.degrees(heading_rad) + 360) % 360
        
        # Matplotlib orientation for a triangle pointing UP (along Y) is 0 radians.
        # To point in a direction relative to the screen's Y-axis (North), we need to adjust.
        # The angle provided to RegularPolygon is in radians counter-clockwise from the +X axis.
        # To make the "top" of the triangle point towards the calculated heading (CW from North),
        # we use this transformation:
        marker_orientation_rad = math.radians(-90 + heading_deg)
        altitude = heading_deg * 10
        heading_deg = (heading_deg +90 +360) % 360
        
        # return x, y, heading_deg, marker_orientation_rad
        latest_data = [x,y, heading_deg, marker_orientation_rad,altitude]
        if data_queue.full():
            data_queue.get_nowait()
        data_queue.put(latest_data)
 
        # print("compute heading_deg= ",heading_deg)
        time.sleep(0.01) 

## ----------------------------------------------  retrieve data from CSV file -------

df = None
def read_csv_file(file_path):
     global df
     try:
         # Reading CSV into the global DataFrame
         print("CSV file read begun.")
         df = pd.read_csv(file_path, sep=';',header=0)
         print("CSV file has been read successfully.")
     except FileNotFoundError:
         print(f"Error: File '{file_path}' not found.")
     except pd.errors.EmptyDataError:
         print("Error: The CSV file is empty.")
     except pd.errors.ParserError:
         print("Error: There was an issue parsing the CSV file.")

def retrieve_csv_data(data_queue):
    global df
    row = 0
    read_csv_file(file_name)
    while not stop_event.is_set():

        orientation = float(df.at[row,'HDG'])
        X_offset = float(df.at[row,'EW_POS'])
        Y_offset = float(df.at[row,'NS_POS'])
        altitude = float(df.at[row,'ALT'])
        marker_orientation_rad = math.radians(orientation-180) * -1.0
        orientation = orientation * -1.0
        #print(marker_orientation_rad,X_offset,Y_offset)
        #print ("hdg ",orientation)
        latest_data = [X_offset, Y_offset, orientation, marker_orientation_rad,altitude]
        if data_queue.full():
            data_queue.get_nowait()
        data_queue.put(latest_data)

        row = row + 1
        time.sleep(0.01)

## ----------------------------------------------  retrieve data from serial port -------

SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600
# Define the start and end bytes
START_BYTE = b'\xf0'
END_BYTE = b'\x0f'
RECORD_LENGTH = 22 # Total length including start and end bytes (1 + 10 data + 1)

def parse_serial_data(data_queue):
    """
    Reads binary data from a serial device and extracts records.
    """
    try:
        # Open the serial port
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to serial port {SERIAL_PORT} at {BAUD_RATE} baud.")
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        return -999,0,0

    buffer = b''
    while not stop_event.is_set():
        try:
            # Read all available bytes from the serial buffer
            data = ser.read(ser.in_waiting or 1)
            if data:
                buffer += data

                # Process the buffer for records
                while True:
                    # Look for the start byte
                    start_index = buffer.find(START_BYTE)
                    if start_index == -1:
                        # No start byte found, discard buffer (or wait for more data)
                        # A better approach might be to implement a timeout on the buffer
                        # to prevent it from growing indefinitely with bad data.
                        break

                    # Discard any data before the start byte
                    if start_index > 0:
                        buffer = buffer[start_index:]
                        start_index = 0 # Now start is at index 0

                    # Check if we have enough data for a full record
                    if len(buffer) >= RECORD_LENGTH:
                        # Check the end byte
                        if buffer[RECORD_LENGTH - 1:RECORD_LENGTH] == END_BYTE:
                            # Valid record found
                            record = buffer[:RECORD_LENGTH]
                            orientation,marker_orientation_rad,X_offset,Y_offset, altitude = process_record(record)
                            latest_data = [X_offset, Y_offset, orientation, marker_orientation_rad,altitude]
                            if data_queue.full():
                                data_queue.get_nowait()
                            data_queue.put(latest_data)
                            # return marker_orientation_rad,X_offset,Y_offset
                            # Remove the processed record from the buffer
                            buffer = buffer[RECORD_LENGTH:]
                        else:
                            # The expected end byte is missing at the 12th position,
                            # implying a synchronization issue or invalid data.
                            # Discard the start byte and continue the search.
                            buffer = buffer[1:]
                    else:
                        # Not enough data for a full record yet, wait for more data
                        break

        except KeyboardInterrupt:
            print("Serial reading stopped by user.")
            break
        except Exception as e:
            print(f"An error occurred during serial communication: {e}")
            break

    ser.close()

def process_record(record_bytes):
    """
    Parses the 22-byte record and prints the data.
    """
    # The record format is: START_BYTE (1 byte), data (10 bytes), END_BYTE (1 byte)
    # Extract the 10 data bytes
    data_payload = record_bytes[1:RECORD_LENGTH - 1]

    # You can unpack the data payload based on its specific structure
    # For this example, we just print the raw bytes and a hex representation
    # print("-" * 40)
    # print(f"Received Record (22 bytes): {record_bytes.hex()}")
    # print(f"Data Payload (20 bytes): {data_payload.hex()}")
   
    try:
        internal_data = record_bytes[1:-1]
        #unpacked_data_size = struct.calcsize('>hhhfff') # > for big-endian
        #print(f" calcsize = {unpacked_data_size}")
        unpacked_data = struct.unpack('>BhhhfffB', internal_data) # > for big-endian
        #print(f"  Unpacked Data (big-endian): {unpacked_data}")
        print(unpacked_data[1]/100.0,";",unpacked_data[2]/100.0,";",unpacked_data[3]/100.0,";",unpacked_data[4],";",unpacked_data[5],";",unpacked_data[6])
        orientation = (unpacked_data[1]/100.0) 
        altitude = unpacked_data[4]
        X_offset = unpacked_data[5]
        Y_offset = unpacked_data[6]
        marker_orientation_rad = math.radians(orientation-180) * -1.0
        orientation = orientation * -1.0
        #print(marker_orientation_rad,X_offset,Y_offset)
        # print ("hdg ",orientation)
        return orientation,marker_orientation_rad,X_offset,Y_offset, altitude
    except struct.error:
        print("  Could not unpack data using the specified struct format.")



## ---------------------------------  retrieve data from source and update graph  -------

def update(frame, line, aircraft_marker, t_data):
    """Update function for the animation."""
    global text_box
    t = t_data[0]
    
    # Generate new coordinates and heading from the simulation
    # x_new, y_new, _, marker_orientation = generate_figure_eight(t)
    # CSV marker_orientation, x_new, y_new = retrieve_csv_data(t_data[0])
    #marker_orientation, x_new, y_new = parse_serial_data(SERIAL_PORT, BAUD_RATE)
    try:
        x_new, y_new, heading_deg, marker_orientation, altitude = data_queue.get_nowait()
        print("from queue heading_deg= ",heading_deg, "alt=",altitude)
        x_new = 1.0 * x_new 
        y_new = -1.0 * y_new 

        t_data[0] += 1 # Increment time step
        
        # Append new data to the path history
        flight_path_x.append(x_new)
        flight_path_y.append(y_new)
        
        # Update the entire flight path line
        line.set_data(flight_path_x, flight_path_y)
        
        # Update the aircraft marker's position and orientation
        aircraft_marker.xy = (x_new, y_new)
        aircraft_marker.orientation = -1.0 * marker_orientation
        aircraft_marker.orientation += math.radians(180)
        aircraft_scale = scale_aircraft_marker()
        aircraft_marker.radius = MARKER_SIZE * aircraft_scale
        
        text_box.set_val(f'ALT : {altitude:.2f}')

        # Re-draw the canvas to show updates in interactive mode
        fig.canvas.draw_idle()
        
    except queue.Empty:
        # print("no new data found in queue")
        pass

    return line, aircraft_marker,

# --- Main Execution ---
if __name__ == '__main__':
    # global data_queue
    fig, ax, line, aircraft_marker, text_box = initialize_plot()
    
    # Data container for time step (needs to be mutable for FuncAnimation)
    t_step = [1]
    print(f"HDG;PITCH;ROLL;ALT;EW_POS;NS_POS")
   
    # uncomment one of the following three lines to either:
    # read from the rs-232 serial port
    # read from a CSV format flight log 
    # generate data to fly in a figure eight
    io_thread = threading.Thread(target = parse_serial_data,args=(data_queue,),daemon=True)
    #io_thread = threading.Thread(target = retrieve_csv_data,args=(data_queue,),daemon=True)
    #io_thread = threading.Thread(target = generate_figure_eight,args=(data_queue,),daemon=True)

    # start the input thread
    io_thread.start() 
    
    # FuncAnimation handles the live updating in a loop
    # interval=1000 adjusts the speed of the animation in milliseconds
    ani = animation.FuncAnimation(fig, update, fargs=(line, aircraft_marker, t_step), 
                                  interval=1000, blit=False, cache_frame_data=False)
    
    # The Matplotlib toolbar (magnifying glass icon) provides interactive zoom/pan
    plt.show()
