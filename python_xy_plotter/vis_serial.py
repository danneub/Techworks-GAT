import serial
import struct
import time
import threading
#   this script will read the serial port, interpret the incoming data, dump it to SDTOUT as a CSV format file
# to generate a file, just pipe the output into a file 
#   python vis_serial.py > flight_data_csv.log  



# Define the start and end bytes
START_BYTE = b'\xf0'
END_BYTE = b'\x0f'
RECORD_LENGTH = 22 # Total length including start and end bytes (1 + 10 data + 1)

def parse_serial_data(port_name, baud_rate):
    """
    Reads binary data from a serial device and extracts records.
    """
    try:
        # Open the serial port
        ser = serial.Serial(port_name, baud_rate, timeout=1)
        print(f"Connected to serial port {port_name} at {baud_rate} baud.")
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        return

    buffer = b''
    while True:
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
                            process_record(record)
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
    except struct.error:
        print("  Could not unpack data using the specified struct format.")


if __name__ == "__main__":
    # !!! IMPORTANT: Change 'COM3' to your serial port name (e.g., '/dev/ttyUSB0' on Linux, 'COM1' on Windows)
    # and adjust the baud rate to match your device.
    SERIAL_PORT = '/dev/ttyUSB0' 
    BAUD_RATE = 9600
    print(f"Parsing records from /dev/ttyUSB0 ...")
    print(f"HDG;PITCH;ROLL;ALT;EW_POS;NS_POS")

    # Running the parser in a separate thread so the main program can handle other things
    # or just run it directly if it's the only task.
    # serial_thread = threading.Thread(target=parse_serial_data, args=(SERIAL_PORT, BAUD_RATE))
    # serial_thread.daemon = True
    # serial_thread.start()

    # To run directly:
    parse_serial_data(SERIAL_PORT, BAUD_RATE)
