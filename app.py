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

# ---- Node model: edit these to match the real hardware ----
PANEL_RATED_W = 100          # nameplate rating of the panel
PANEL_DERATE = 0.75          # field output is roughly 70-80% of nameplate
PANEL_PEAK_W = PANEL_RATED_W * PANEL_DERATE   # about 75 W at solar noon
LOAD_W = 15                  # node draw while running
METER = os.environ.get("METER", "SIMULATED")  # METER=REAL once hardware is attached
NODE_TZ = os.environ.get("NODE_TZ", "Africa/Johannesburg")

try:
    from zoneinfo import ZoneInfo
    NODE_ZONE = ZoneInfo(NODE_TZ)
except Exception:
    NODE_ZONE = datetime.timezone(datetime.timedelta(hours=2))


def _local_hour():
    t = datetime.datetime.now(NODE_ZONE)
    return t.hour + t.minute / 60 + t.second / 3600


def _simulated_watts():
    h = _local_hour()
    if h < 6 or h > 18:
        return 0.0
    return PANEL_PEAK_W * math.sin(math.pi * (h - 6) / 12)


def _simulated_wh_24h():
    # clear-sky day: area under the half-sine, peak * 12 h * 2 / pi
    return PANEL_PEAK_W * 12 * 2 / math.pi


def _meter_watts():
    # Hardware hook: return panel watts from the real meter.
    raise NotImplementedError("No meter attached yet")


def _meter_wh_24h():
    # Hardware hook: return panel Wh measured over the last 24 hours.
    raise NotImplementedError("No meter attached yet")


def read_watts():
    """Panel output now. Returns (watts, source): REAL or SIMULATED."""
    if METER == "REAL":
        return _meter_watts(), "REAL"
    return _simulated_watts(), "SIMULATED"


def read_solar_wh_24h():
    """Panel energy over the trailing 24 hours."""
    if METER == "REAL":
        return _meter_wh_24h()
    return _simulated_wh_24h()


@app.post("/job")
def job(rounds: int = 2_000_000):
    t0 = time.perf_counter()
    h = b"solarnode"
    for _ in range(rounds):
        h = hashlib.sha256(h).digest()
    secs = time.perf_counter() - t0
    solar_w, source = read_watts()
    solar_wh_24h = read_solar_wh_24h()
    load_wh_24h = LOAD_W * 24
    rec = {
        "node": "sim-1", "rounds": rounds, "hash": h.hex(),
        "secs": round(secs, 2),
        "solar_w": round(solar_w, 1),
        "load_w": LOAD_W,
        "solar_wh": round(solar_w * secs / 3600, 5),
        "load_wh": round(LOAD_W * secs / 3600, 5),
        "solar_wh_24h": round(solar_wh_24h, 1),
        "load_wh_24h": load_wh_24h,
        "net_wh_24h": round(solar_wh_24h - load_wh_24h, 1),
        "source": source,
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
