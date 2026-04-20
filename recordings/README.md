# Recordings

Place ZED SVO recording files here. SVO files are not tracked by git (they can be several gigabytes each).

## File format

ZED cameras save recordings in the `.svo` or `.svo2` format. Both are supported.

## How to record

With a ZED camera connected, use the ZED Explorer application or the ZED SDK to capture an SVO file. Save the output into this directory.

## How to replay

Pass `--svo --svo-file <path>` to the launcher:

```bash
./run.sh --svo --svo-file recordings/my-run.svo
./run.sh --svo --svo-file recordings/my-run.svo --loop   # loop continuously
```
