import hashlib, json, math, os, time, datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from xrpl.clients import JsonRpcClient
from xrpl.wallet import Wallet, generate_faucet_wallet
from xrpl.models.transactions import AccountSet, Memo
from xrpl.models.requests import AccountTx
from xrpl.transaction import submit_and_wait

client = JsonRpcClient("https://s.altnet.rippletest.net:51234")
if os.path.exists("wallet.txt"):
    wallet = Wallet.from_seed(open("wallet.txt").read().strip())
else:
    wallet = generate_faucet_wallet(client)
    open("wallet.txt", "w").write(wallet.seed)

app = FastAPI()
LOAD_W = 15

def solar_watts():
    t = datetime.datetime.now()
    h = t.hour + t.minute / 60
    return max(0, 400 * math.sin(math.pi * (h - 6) / 12))

@app.post("/job")
def job(rounds: int = 2_000_000):
    t0 = time.perf_counter()
    h = b"solarnode"
    for _ in range(rounds):
        h = hashlib.sha256(h).digest()
    secs = time.perf_counter() - t0
    rec = {
        "node": "sim-1", "rounds": rounds, "hash": h.hex(),
        "secs": round(secs, 2),
        "wh": round(LOAD_W * secs / 3600, 5),
        "solar_pct": round(min(100, solar_watts() / LOAD_W * 100)),
        "ts": int(time.time()),
    }
    memo = Memo(memo_type=b"solarnode".hex(),
                memo_data=json.dumps(rec).encode().hex())
    submit_and_wait(AccountSet(account=wallet.address, memos=[memo]),
                    client, wallet)
    return rec

@app.get("/log")
def log():
    txs = client.request(
        AccountTx(account=wallet.address, limit=20)).result["transactions"]
    out = []
    for x in txs:
        t = x.get("tx_json") or x.get("tx") or {}
        for m in t.get("Memos", []):
            out.append(json.loads(
                bytes.fromhex(m["Memo"]["MemoData"]).decode()))
    return out

PAGE = """<meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:sans-serif;background:#111;color:#fb3;padding:16px">
<h2>SolarNode sim</h2>
<button onclick="go()" style="font-size:22px;padding:16px 24px">Run job</button>
<pre id=o style="white-space:pre-wrap;word-break:break-all"></pre>
<script>
async function go(){o.textContent='running...';
await fetch('/job',{method:'POST'});load()}
async function load(){const r=await(await fetch('/log')).json();
o.textContent=r.map(x=>JSON.stringify(x,null,1)).join('\\n')}
load()
</script>"""

@app.get("/", response_class=HTMLResponse)
def home():
    return PAGE
