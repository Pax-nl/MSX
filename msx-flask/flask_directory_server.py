#!/usr/bin/env python3
"""
Flask webserver that returns plain text directory listing from files/ directory
"""


import os
from flask import Flask, request, Response
from dotenv import load_dotenv


load_dotenv()
PORT = int(os.getenv("PORT", 5001))
app = Flask(__name__)

# Configure the directory to serve - set to files subdirectory
BASE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
SERVE_DIRECTORY = os.path.join(BASE_DIRECTORY, "files")


@app.route("/index2.php/")
def directory_listing():
    """Return directory listing based on type parameter (ROM or DSK)"""

    # Get query parameters
    request_type = request.args.get("type", "ROM").upper()
    request_char = request.args.get("char", "a")
    download_index = request.args.get("download", None)

    # Always print debug info since we can't control the embedded device calls
    print(
        f"\n=== API Request: type={request_type}, char={request_char}, download={download_index} ==="
    )

    # Determine if we should filter by name
    filter_by_name = request_char != "a"
    if filter_by_name:
        print(f"Will filter games containing: '{request_char}' (case-insensitive)")
    else:
        print("Showing all games (char=a)")

    # Check if files directory exists
    if not os.path.exists(SERVE_DIRECTORY) or not os.path.isdir(SERVE_DIRECTORY):
        print("ERROR: files directory not found")
        return "Error: files directory not found", 404

    try:
        # Determine file extensions to look for based on type
        if request_type == "ROM":
            extensions = [".rom", ".ROM"]
        elif request_type == "DSK":
            extensions = [".dsk", ".DSK"]
        else:
            print(f"ERROR: Unsupported type '{request_type}'")
            return f"Error: Unsupported type '{request_type}'. Use ROM or DSK.", 400

        print(f"Looking for extensions: {extensions}")
        print(f"Scanning directory: {SERVE_DIRECTORY}")

        # Scan files/ directory for files matching the requested type
        files = []

        # Get all files with matching extensions
        all_files = os.listdir(SERVE_DIRECTORY)
        print(f"All files in directory: {all_files}")

        for item_name in all_files:
            if any(item_name.endswith(ext) for ext in extensions):
                print(f"  MATCH: {item_name}")
                item_path = os.path.join(SERVE_DIRECTORY, item_name)
                if os.path.isfile(item_path):
                    try:
                        # Get file size in bytes
                        size = os.path.getsize(item_path)

                        # Remove extension from filename
                        # Find the last dot and remove everything from there
                        dot_index = item_name.rfind(".")
                        if dot_index != -1:
                            game_name = item_name[:dot_index]
                        else:
                            game_name = item_name

                        # Clean up filename to match original server format
                        # Remove " [original]" text that appears in some filenames
                        game_name = game_name.replace(" [original]", "")

                        # Remove space before final bracket only when there's already a bracket before it
                        # This handles cases like "[v1.0] [5401]" -> "[v1.0][5401]"
                        # But keeps "(2017) [6702]" as "(2017) [6702]"
                        import re

                        game_name = re.sub(r"(\]\s)(\[\d+\])$", r"]\2", game_name)

                        # Apply name filtering if char != "a"
                        if filter_by_name:
                            search_term_lower = request_char.lower()
                            game_name_lower = game_name.lower()
                            print(
                                f"    FILTER CHECK: '{game_name}' -> comparing '{game_name_lower}' contains '{search_term_lower}'"
                            )
                            if search_term_lower not in game_name_lower:
                                print(
                                    f"    FILTERED OUT: '{game_name}' (doesn't contain '{request_char}')"
                                )
                                continue
                            else:
                                print(
                                    f"    FILTER MATCH: '{game_name}' contains '{request_char}'"
                                )

                        print(f"    Added: '{game_name}' (size: {size})")

                        # Add to list as tuple for sorting
                        files.append((game_name, size))
                    except (OSError, IOError):
                        # Skip files we can't read
                        print(f"    ERROR: Could not read {item_name}")
                        continue
            else:
                print(f"  SKIP: {item_name} (no matching extension)")

        # Sort by game name and remove duplicates
        files = sorted(list(set(files)))

        print(f"Final file list ({len(files)} files):")
        for game_name, size in files:
            print(f"  - {game_name} ({size} bytes)")
        print("=== END API Processing ===\n")

        # Check if this is a download request
        if download_index is not None and download_index.isdigit():
            download_idx = int(download_index)
            if 0 <= download_idx < len(files):
                game_name, size = files[download_idx]
                print(f"DOWNLOAD REQUEST: Index {download_idx} -> {game_name}")

                # Find the actual file on disk
                for item_name in os.listdir(SERVE_DIRECTORY):
                    if any(item_name.endswith(ext) for ext in extensions):
                        item_path = os.path.join(SERVE_DIRECTORY, item_name)
                        if os.path.isfile(item_path):
                            # Remove extension and clean up name to match
                            dot_index = item_name.rfind(".")
                            clean_name = (
                                item_name[:dot_index] if dot_index != -1 else item_name
                            )
                            clean_name = clean_name.replace(" [original]", "")
                            import re

                            clean_name = re.sub(r"(\]\s)(\[\d+\])$", r"]\2", clean_name)

                            if clean_name == game_name:
                                # Read the file content
                                try:
                                    with open(item_path, "rb") as f:
                                        file_content = f.read()

                                    # Create metadata header like PHP server
                                    if request_type == "DSK":
                                        header = f"size:{len(file_content)},disks:1,name:{game_name}.{request_type.lower()}"
                                    else:  # ROM
                                        header = f"type:,start:,size:{len(file_content)},name:{game_name}.{request_type.lower()}"

                                    print(
                                        f"DOWNLOAD: Sending {len(file_content)} bytes for {game_name}"
                                    )

                                    # Return file with metadata header
                                    def generate():
                                        yield header.encode("utf-8")
                                        yield b"\n"
                                        yield file_content

                                    response = Response(
                                        generate(), mimetype="application/octet-stream"
                                    )
                                    response.headers["Expires"] = "0"
                                    response.headers["Cache-Control"] = (
                                        "no-store, no-cache, must-revalidate"
                                    )
                                    return response

                                except (OSError, IOError) as e:
                                    return f"Error reading file: {str(e)}", 500

                return f"Error: File not found for download index {download_idx}", 404
            else:
                return (
                    f"Error: Invalid download index {download_idx}. Valid range: 0-{len(files)-1}",
                    400,
                )

        # Format as tab-separated lines with newlines (matching PHP behavior)
        if files:
            result = ""
            for game_name, size in files:
                result += f"{game_name}\t{size}\n"
        else:
            result = "No files found\t0\n"

        # Return as plain text with cache control headers matching PHP server
        # Use streaming response to enable chunked encoding like the original PHP server
        def generate():
            yield result

        response = Response(generate(), mimetype="text/plain")
        response.headers["Expires"] = "0"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return response

    except (OSError, IOError) as e:
        return f"Error reading directory: {str(e)}", 500


@app.route("/")
def index():
    """Root route with simple information"""
    return """Flask Directory Server - Single API Endpoint
Endpoint: /index2.php/
Parameters: 
  - type=ROM (default) | DSK
  - char=a (shows all) | any_text (filters by name, case-insensitive)
Examples:
  - /index2.php/?type=ROM&char=a (shows all .rom files)
  - /index2.php/?type=DSK&char=a (shows all .dsk files)
  - /index2.php/?type=ROM&char=Super (shows .rom files with 'Super' in name)
  - /index2.php/?type=DSK&char=moon (shows .dsk files with 'moon' in name)
Format: Tab-separated game names and sizes
Debug: Always enabled - check server console for detailed logs
"""


# Catch-all route for any other requests
@app.route("/<path:path>")
def catch_all(path):
    """Catch all other routes and redirect or return error"""
    return f"404 - Path not found: /{path}\nOnly /index2.php/ is supported", 404


if __name__ == "__main__":
    print(f"Base directory: {BASE_DIRECTORY}")
    print(f"Serving directory: {SERVE_DIRECTORY}")
    print("Starting Flask server...")

    # Check directory and count files
    if os.path.exists(SERVE_DIRECTORY):
        try:
            rom_count = len(
                [
                    f
                    for f in os.listdir(SERVE_DIRECTORY)
                    if f.endswith(".rom") or f.endswith(".ROM")
                ]
            )
            dsk_count = len(
                [
                    f
                    for f in os.listdir(SERVE_DIRECTORY)
                    if f.endswith(".dsk") or f.endswith(".DSK")
                ]
            )
            print(
                f"Found {rom_count} ROM files and {dsk_count} DSK files in files/ directory"
            )
        except Exception as e:
            print(f"Error scanning directory: {e}")
    else:
        print("WARNING: files/ directory not found!")

    # Run the Flask app
    app.run(debug=True, host="0.0.0.0", port=PORT)
