# aXet-C1

Internal Assignments

## LogScope acceptance checks

Putting the verification commands in the repository makes the handoff and grading flow reproducible.

Run all commands from Windows through WSL Ubuntu.

### 1. All three commands work on `samples/sample.log`

```bash
# 1a. summary works on samples/sample.log
wsl -d Ubuntu --cd /mnt/c/Users/clarence.quek/Documents/assignment/axet/C1/aXet-C1 -- /bin/sh -lc '. .venv/bin/activate && python -m logscope summary samples/sample.log'
```

```bash
# 1b. timeline works on samples/sample.log
wsl -d Ubuntu --cd /mnt/c/Users/clarence.quek/Documents/assignment/axet/C1/aXet-C1 -- /bin/sh -lc '. .venv/bin/activate && python -m logscope timeline samples/sample.log --bucket 15m'
```

```bash
# 1c. grep works on samples/sample.log
wsl -d Ubuntu --cd /mnt/c/Users/clarence.quek/Documents/assignment/axet/C1/aXet-C1 -- /bin/sh -lc '. .venv/bin/activate && python -m logscope grep samples/sample.log --level ERROR --since "2026-10-01 08:00"'
```

### 2. Run the unit test suite

```bash
wsl -d Ubuntu --cd /mnt/c/Users/clarence.quek/Documents/assignment/axet/C1/aXet-C1 -- /bin/sh -lc '. .venv/bin/activate && pytest -q'
```

### 3. Generate 10 MB and 100 MB logs and run the benchmark

```bash
# 3a. create the bench/ output directory
wsl -d Ubuntu --cd /mnt/c/Users/clarence.quek/Documents/assignment/axet/C1/aXet-C1 -- /bin/sh -lc 'mkdir -p bench'
```

```bash
# 3b. generate a 10 MB log
wsl -d Ubuntu --cd /mnt/c/Users/clarence.quek/Documents/assignment/axet/C1/aXet-C1 -- /bin/sh -lc '. .venv/bin/activate && python scripts/gen_log.py --size 10MB --out bench/small.log --seed 42 --malformed-rate 0.03'
```

```bash
# 3c. generate a 100 MB log
wsl -d Ubuntu --cd /mnt/c/Users/clarence.quek/Documents/assignment/axet/C1/aXet-C1 -- /bin/sh -lc '. .venv/bin/activate && python scripts/gen_log.py --size 100MB --out bench/big.log --seed 42 --malformed-rate 0.03'
```

```bash
# 3d. benchmark the 10 MB log
wsl -d Ubuntu --cd /mnt/c/Users/clarence.quek/Documents/assignment/axet/C1/aXet-C1 -- /bin/sh -lc '. .venv/bin/activate && python scripts/bench.py bench/small.log'
```

```bash
# 3e. benchmark the 100 MB log
wsl -d Ubuntu --cd /mnt/c/Users/clarence.quek/Documents/assignment/axet/C1/aXet-C1 -- /bin/sh -lc '. .venv/bin/activate && python scripts/bench.py bench/big.log'
```

```bash
# 3f. view the recorded results
wsl -d Ubuntu --cd /mnt/c/Users/clarence.quek/Documents/assignment/axet/C1/aXet-C1 -- /bin/sh -lc 'cat BENCHMARK.md'
```

### 4. Malformed-line count is reported by every command

```bash
wsl -d Ubuntu --cd /mnt/c/Users/clarence.quek/Documents/assignment/axet/C1/aXet-C1 -- /bin/sh -lc '. .venv/bin/activate && python -m logscope grep samples/sample.log 1>/dev/null'
```

### 5. Check git history for plan-then-build commits

```bash
wsl -d Ubuntu --cd /mnt/c/Users/clarence.quek/Documents/assignment/axet/C1/aXet-C1 -- /bin/sh -lc 'git log --oneline --decorate --graph -n 12'
```
