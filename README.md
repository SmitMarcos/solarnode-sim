# SolarNode Sim

A working software prototype for SolarNode: solar-powered compute with energy use that anyone can verify.

A job runs, produces a deterministic hash, has its energy use calculated, and is logged to the XRPL testnet. A dashboard reads the record back from the chain.

> Status: prototype. Solar input is simulated and the ledger is XRPL testnet only.

## How it works

1. **Job runner**: chained SHA-256 (default 2,000,000 rounds from a fixed seed). Integer-only, so every machine returns the same hash for the same input.
2. **Energy model**: watt-hours = node load x job duration. Solar % comes from a simulated sun curve (6am to 6pm).
3. **Ledger**: each job is written to XRPL testnet as a transaction memo containing node ID, rounds, hash, seconds, Wh, solar % and timestamp.
4. **Dashboard**: a touch-friendly page with a Run job button that reads the records back from the chain.

## Run it

    pip install fastapi uvicorn xrpl-py
    uvicorn app:app --port 8000

Open port 8000 in a browser and tap Run job. On first start a testnet wallet is created from the faucet and saved to wallet.txt. Never commit wallet.txt.

## Endpoints

- POST /job runs a job, logs it on-chain and returns the record
- GET /log returns the latest records read back from XRPL
- GET / is the dashboard

## Verify it

For 2,000,000 rounds the final hash must be:

    3c1612621854ec902e7a5999a03fc195e98c488cb57cddac9a0e74079f6517c8

Any machine that gets a different hash is not running the same workload.

## Limitations

- Solar data is simulated.
- Energy figures are self-reported by the node. The chain proves a record was written and not altered afterwards, not that the meter reading was true.
- Testnet only. No real value moves.

## Roadmap

- Real meter input on a Raspberry Pi (same code, new energy source)
- Hardware-signed meter readings
- Lease and payment logic for compute

Built from an iPad in GitHub Codespaces.
