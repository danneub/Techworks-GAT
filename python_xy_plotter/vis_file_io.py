import struct

def parse_f0_0f_records(filename):
     """
     A generator that reads a binary file and yields 12-byte records
     starting with 0xf0 and ending with 0x0f.

     Args:
         filename (str): The path to the binary data file.

     Yields:
         bytes: A valid 12-byte data record (including the start/end
delimiters).
     """
     start_marker = b'\xf0'
     end_marker = b'\x0f'
     record_size = 20

     try:
         with open(filename, 'rb') as f:
             # Read the entire file content for simplicity in scanning
             # For very large files, a more complex buffer-based approach would be better
             data = f.read()
     except IOError as e:
         print(f"Error opening or reading file: {e}")
         return

     i = 0
     while i + record_size <= len(data):
         # Check if the current 12-byte chunk starts with f0 and ends with 0f
         if data[i] == start_marker[0] and data[i + record_size - 1] == end_marker[0]:
             record = data[i:i + record_size]
             yield record
             # Move to the end of the current record to find the next potential start
             i += record_size
         else:
             # If not a valid record, advance one byte and try again
             i += 1

# --- Example Usage ---
# 
# # 1. Create a dummy data file for testing
# dummy_filename = "data_records.bin"
# try:
#      with open(dummy_filename, 'wb') as f:
#          # Valid record 1: F0 [10 bytes of data including F0/0F] 0F
# f.write(b'\xf0\x01\x02\x03\x04\x05\x06\x07\x08\xf0\x0f\x0f')
#          # Junk data
#          f.write(b'\xaa\xbb\xcc')
#          # Valid record 2: F0 [10 bytes of data] 0F
# f.write(b'\xf0\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x0f')
#          # Another F0 followed by junk
#          f.write(b'\xf0\xde\xad\xbe\xef')
# except IOError as e:
#      print(f"Error creating dummy file: {e}")
#      exit()

#vis_filename = "gat_vis_CAPTURE_1_9_2026.TXT"
vis_filename = "flight_data_1_16_2026.txt"
# 2. Run the parser on the dummy file
print(f"Parsing records from '{vis_filename}'...")
print(f"  RAW      ;  HDG ; PITCH ; ROLL ; ALT ; EW_POS ; NS_POS ")
for idx, record_bytes in enumerate(parse_f0_0f_records(vis_filename)):
     #print(f"\nFound Record {idx + 1}:")
     #print(f"  Raw Bytes: {record_bytes.hex()}")
     #print(f"{record_bytes.hex()}", end=" ; ")

     # Optional: Example of unpacking internal data if its structure is known
     # Assuming the 20 internal bytes are 5 big-endian unsigned short integers (H)
     try:
         internal_data = record_bytes[1:-1]
         #unpacked_data_size = struct.calcsize('>hhhfff') # > for big-endian
         #print(f" calcsize = {unpacked_data_size}")
         unpacked_data = struct.unpack('>hhhfff', internal_data) # > for big-endian
         #print(f"  Unpacked Data (big-endian): {unpacked_data}")
         print(unpacked_data[0]/100.0,";",unpacked_data[1]/100.0,";",unpacked_data[2]/100.0,";",unpacked_data[3],";",unpacked_data[4],";",unpacked_data[5])
     except struct.error:
         print("  Could not unpack data using the specified struct format.")


