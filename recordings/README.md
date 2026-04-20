# Recordings

Place ZED SVO recording files here. SVO files are not tracked by git (they can be several gigabytes each).

You can find recordings from this drive: [Zed Mini Campus Recordings](https://drive.google.com/drive/u/3/folders/13NbSXXYstn-2NNlI8K3TLkBbLt9HyD1F)

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
