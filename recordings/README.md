# Recordings

Place ZED SVO recording files here. SVO files are not tracked by git (they can be several gigabytes each).

## File format

ZED cameras save recordings in the `.svo` or `.svo2` format. Both are supported.

## How to record

With a ZED camera connected, use the ZED Explorer application or the ZED SDK to capture an SVO file. Save the output into this directory.

## How to replay

Pass `--svo` to the launcher. It defaults to the first `.svo` file found in this directory, or you can specify a file explicitly:

```bash
./run.sh --svo
./run.sh --svo --svo-file recordings/my-run.svo
./run.sh --svo --loop   # loop the recording continuously
```

## Current default

The launcher defaults to:

```
recordings/CSUN-outside-iii.svo
```

Change the `SVO_FILE` variable at the top of `run.sh` to point to a different default file.
