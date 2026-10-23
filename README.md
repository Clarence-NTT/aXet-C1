# aXet-C1

Internal Assignments

## LogScope acceptance checks

Yes — this is a good idea. Putting the verification commands in the repository makes the handoff and grading flow reproducible.

Run all commands from Windows through WSL Ubuntu.

### 1. Verify the three commands on `samples/sample.log`

```bash
wsl -d Ubuntu --cd /mnt/c/Users/clarence.quek/Documents/assignment/axet/C1/aXet-C1 -- /bin/sh -lc '. .venv/bin/activate && python -m logscope summary samples/sample.log && python -m logscope timeline samples/sample.log --bucket 15m && python -m logscope grep samples/sample.log --level ERROR --since "2026-10-01 09:00"'
```

### 2. Run the unit test suite

```bash
wsl -d Ubuntu --cd /mnt/c/Users/clarence.quek/Documents/assignment/axet/C1/aXet-C1 -- /bin/sh -lc '. .venv/bin/activate && pytest -q'
```

### 3. Generate a 100 MB log and run the benchmark

```bash
wsl -d Ubuntu --cd /mnt/c/Users/clarence.quek/Documents/assignment/axet/C1/aXet-C1 -- /bin/sh -lc '. .venv/bin/activate && mkdir -p bench && python scripts/gen_log.py --size 100MB --out bench/big.log --seed 42 --malformed-rate 0.03 && python scripts/bench.py bench/big.log && cat BENCHMARK.md'
```

### 4. Check git history for plan-then-build commits

```bash
wsl -d Ubuntu --cd /mnt/c/Users/clarence.quek/Documents/assignment/axet/C1/aXet-C1 -- /bin/sh -lc 'git log --oneline --decorate --graph -n 12'
```
