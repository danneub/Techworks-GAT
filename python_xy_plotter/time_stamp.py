import time


count = 0

while count < 100:
    current_time = time.time()

    print(count,"  ", current_time)
    count = count + 1
