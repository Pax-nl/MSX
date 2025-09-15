# MSX Flask Directory Server

A tiny Flask-based web server that emulates a legacy PHP endpoint (`/index2.php/`) to list and download MSX ROM (`.rom`) and disk (`.dsk`) images stored in a local `msx/` directory.
files/ directory.
The endpoint returns a plain text, tab-separated listing (game name + size in bytes) and supports:
- Filtering by substring (case-insensitive)
- Selecting media type: ROM or DSK
- Downloading a specific file by index (with a metadata header to mimic original server behavior)

---
## Features
- Single endpoint: `/index2.php/`
- Cleaned / normalized game names (removes extensions, trims some bracket spacing artifacts)
- Deterministic sorted output; duplicate logical names collapsed
- Always-on server-side debug logging to stdout for embedded device troubleshooting
- Simple download mechanism using `download=<index>`

---
## Quick Start
```bash
# 1. Clone repository
git clone https://github.com/Pax-nl/MSX.git
cd MSX/msx-flask

# 2. (Optional but recommended) Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependency
pip install -r requirements.txt  # (or: pip install Flask)

# 4. Create the data directory and add your ROM/DSK files

mkdir files
cp /path/to/your/*.rom files/
cp /path/to/your/*.dsk files/

# 5. Run the server
python flask_directory_server.py

# Server listens on 0.0.0.0:5001
```

---
## Endpoint
`GET /index2.php/`

### Query Parameters
| Name | Default | Allowed | Description |
|------|---------|---------|-------------|
| `type` | `ROM` | `ROM`, `DSK` | File type filter (by extension) |
| `char` | `a` | any string | Substring filter (case-insensitive). `a` = show all |
| `download` | (none) | integer index | If set, returns file content instead of list |

### Listing Response Format
Plain text. One game per line. Columns separated by a single tab (`\t`). Final line ends with `\n`.
```
<GameName>\t<FileSizeInBytes>
```
If no files match:
```
No files found\t0
```

### Example Listing Requests
```bash
curl 'http://localhost:5001/index2.php/?type=ROM&char=a'
curl 'http://localhost:5001/index2.php/?type=DSK&char=moon'
curl 'http://localhost:5001/index2.php/?type=ROM&char=Super'
```

### Sample Output
```
Aleste 2 [v1.1][5401]\t262144
Moon Patrol (1986) [1234]\t32768
MSX Super Game [9988]\t65536
```

### Downloading a File
First request the list to determine the index (0-based in sorted output). Then:
```bash
curl -v 'http://localhost:5001/index2.php/?type=ROM&char=a&download=2' --output game.bin
```

For ROMs the response starts with a one-line metadata header, then a newline, then raw binary:
```
type:,start:,size:65536,name:MSX Super Game.rom\n<binary data>
```
For DSK images:
```
size:737280,disks:1,name:Moon Patrol (1986).dsk\n<binary data>
```
Be sure to strip the first line if you need a pure binary file.

---
## Name Normalization Rules
During listing & download matching the server:
1. Removes the file extension.
2. Removes the literal substring `" [original]"` if present.
3. Collapses a space before a trailing bracket group like: `"] [5401]" -> "][5401]"`.
4. Uses the cleaned name for sorting and duplicate removal.

---
## Sorting & Indexing
- Files are collected by extension.
- Cleaned `(name, size)` tuples are de-duplicated using a set.
- Result is sorted alphabetically by cleaned name.
- The displayed order defines the `download` index mapping.

---
## Error Cases
| Scenario | HTTP | Message |
|----------|------|---------|
| `msx/` directory missing | 404 | `Error: msx directory not found` |
| Unsupported `type` | 400 | `Error: Unsupported type 'X'. Use ROM or DSK.` |
| Invalid `download` index | 400 | Range error with valid bounds |
| File not found after index match | 404 | File not found for download index |
| I/O problems | 500 | Appropriate error text |
| `files/` directory missing | 404 | `Error: files directory not found` |
---
## Development Notes
- Server runs with `debug=True` on all interfaces (`0.0.0.0`) port `5001`.
- Console output includes:
  - Raw request parameters
  - Matching / filtering decisions
  - Final file list
  - Download diagnostics
- Safe to tail logs while an embedded client probes the endpoint.

---

---
## Docker (Optional Quick Run)
An Alpine-based `Dockerfile` is included.

```bash
# Build the image
docker build -t msx-flask .

# Prepare (or reuse) your ROM/DSK directory

mkdir -p files
cp /path/to/roms/*.rom files/ 2>/dev/null || true
cp /path/to/disks/*.dsk files/ 2>/dev/null || true

# Run the container, mounting the host msx directory

docker run --rm \
  -p 5001:5001 \
  -v "$PWD/files:/app/files" \
  msx-flask


## Docker Compose Example

You can use Docker Compose to run the service and mount your ROM/DSK files and .env configuration:

```yaml
version: '3.8'
services:
  msx-flask:
    container_name: msx-flask
    image: msx-flask
    build: .
    ports:
      - "5001:5001"
    volumes:
      - ./files:/app/files
      - ./env:/app/.env  # Mount your .env file if needed
    environment:
      - PORT=5001  # Optional: override port
```

To start with Docker Compose:

```bash
docker compose up --build
```


# Test listing
curl 'http://localhost:5001/index2.php/?type=ROM&char=a' | head

---
## Testing Ideas
Since output is plain text, you can smoke test with Python:
```python
import requests
print(requests.get('http://localhost:5001/index2.php/?type=ROM&char=a').text.splitlines()[:5])
```
Add unit tests later by extracting listing logic into a helper function.

---
## Extending
Potential enhancements:
- Cache directory scan results (invalidate on mtime change).
- Support ZIP extraction on the fly.
- Add unit tests & CI workflow.

---
## Requirements
See `requirements.txt` (Flask, python-dotenv, and dependencies).

---
## License
Add a license (e.g. MIT) if you plan to share publicly.

---
## Attribution
Created to serve MSX ROM / DSK files to an embedded client expecting a PHP-like endpoint.
