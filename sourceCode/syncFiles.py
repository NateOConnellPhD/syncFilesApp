#!/usr/bin/env python3

import os
import hashlib
import json
import shutil
import csv
import zipfile
from pathlib import Path
from datetime import datetime
import time
import subprocess

# === CONFIGURATION ===
EXCLUDED_FILES = {".DS_Store", "Thumbs.db", ".TemporaryItems", ".Spotlight-V100", ".fseventsd"}

def is_valid_file(path):
    return path.is_file() and path.name not in EXCLUDED_FILES

def get_source_directory():
    config_path = script_dir / "localDataSync/metaData/source_directory.json"
    if config_path.exists():
        with open(config_path, "r") as f:
            path = json.load(f).get("path")
            return Path(path) if path else Path.home() / "Documents"
    else:
        folder_prompt = (
            'POSIX path of (choose folder with prompt "Select the parent folder to monitor for OneDrive syncing")'
        )
        response = subprocess.run(["osascript", "-e", folder_prompt], capture_output=True, text=True)
        selected_path = Path(response.stdout.strip()).resolve()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump({"path": str(selected_path)}, f, indent=2)
        return selected_path

script_dir = Path(__file__).resolve().parent.parent
source_dir = get_source_directory()
backup_dir = script_dir / "localDataSync"
to_upload_dir = backup_dir / "to_upload"
upload_log_dir = backup_dir / "uploadLogs"
metadata_dir = backup_dir / "metaData"
metadata_path = metadata_dir / "onedrive_mirror_metadata.json"
csv_log_path = upload_log_dir / f"upload_log_{datetime.now().strftime('%Y-%m-%d')}.csv"
zip_path = backup_dir / "onedrive_backup_latest.zip"
csv_path = backup_dir / f"backup_status_{datetime.now().strftime('%Y-%m-%d')}.csv"
log_path = backup_dir / "backup_log.txt"

# Ensure required directories exist
upload_log_dir.mkdir(parents=True, exist_ok=True)
metadata_dir.mkdir(parents=True, exist_ok=True)

# Combined dialog for update method and sync check
combined_prompt = (
    'display dialog "Choose how to handle existing staged upload files:'
    ' Append/Update will keep existing files and only add new or modified ones.'
    ' Delete and Replace will erase everything first.\n\nWARNING: If you have not synced your previous backup to OneDrive, '
    'choosing Delete and Replace will remove files that may not have been uploaded yet." '
    'buttons {"Cancel", "Append/Update", "Delete and Replace"} default button "Append/Update"'
)
combined_response = subprocess.run(["osascript", "-e", combined_prompt], capture_output=True, text=True)
if "Cancel" in combined_response.stdout:
    print("❌ Backup cancelled by user.")
    exit(0)
delete_and_replace = "Delete and Replace" in combined_response.stdout

# Ask user if zip should be included
zip_prompt_script = 'display dialog "Include zip backup?\n\n(This may take several minutes depending on your folder size.)" buttons {"No", "Yes"} default button "Yes"'
zip_response = subprocess.run(["osascript", "-e", zip_prompt_script], capture_output=True, text=True)
include_zip = "Yes" in zip_response.stdout

start_time = time.time()

print(f"Using source directory: {source_dir}")
print("Checking metadata...")
if not metadata_path.exists():
    mirror_metadata = {}
    backup_dir.mkdir(parents=True, exist_ok=True)

    def compute_file_hash(path):
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    for src_path in source_dir.rglob("*"):
        if is_valid_file(src_path):
            rel_path = str(src_path.relative_to(source_dir))
            mtime = os.path.getmtime(src_path)
            file_hash = compute_file_hash(src_path)
            mirror_metadata[rel_path] = {"hash": file_hash, "mtime": mtime}

    with open(metadata_path, "w") as f:
        json.dump(mirror_metadata, f, indent=2)

    print("✅ Metadata initialized. No files were copied.")
    exit(0)

if delete_and_replace:
    print("Clearing previous upload folder...")
    if to_upload_dir.exists():
        shutil.rmtree(to_upload_dir)
    to_upload_dir.mkdir(parents=True, exist_ok=True)
else:
    print("Appending to existing upload folder...")
    to_upload_dir.mkdir(parents=True, exist_ok=True)

print("Loading metadata and preparing file list...")
with open(metadata_path, "r") as f:
    mirror_metadata = json.load(f)

log_entries = []
all_files = []

for item in source_dir.iterdir():
    if item.is_dir():
        latest_mtime = max((os.path.getmtime(f) for f in item.rglob("*") if is_valid_file(f)), default=0)
        any_new_or_modified = False
        for file in item.rglob("*"):
            if not is_valid_file(file):
                continue
            rel_path = str(file.relative_to(source_dir))
            file_mtime = os.path.getmtime(file)
            existing_entry = mirror_metadata.get(rel_path)
            if not existing_entry or file_mtime > existing_entry["mtime"]:
                any_new_or_modified = True
                break
        if any_new_or_modified:
            all_files.extend([f for f in item.rglob("*") if is_valid_file(f)])
        else:
            print(f"Skipping unchanged folder: {item.name}")
    elif is_valid_file(item):
        all_files.append(item)

print(f"🔍 Files selected for evaluation: {len(all_files)}")

def compute_file_hash(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

for i, src_path in enumerate(all_files, 1):
    print(f"Processing file {i} of {len(all_files)}: {src_path.name}")
    rel_path = str(src_path.relative_to(source_dir))
    mtime = os.path.getmtime(src_path)
    file_hash = compute_file_hash(src_path)

    existing_entry = mirror_metadata.get(rel_path)
    if not existing_entry:
        status = "new"
    elif file_hash != existing_entry["hash"] or mtime > existing_entry["mtime"]:
        status = "modified"
    else:
        status = "unchanged"

    if status in {"new", "modified"}:
        dest_path = to_upload_dir / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src_path, dest_path)
        except Exception as e:
            print(f"Failed to copy {src_path}: {e}")

    log_entries.append([rel_path, status])
    mirror_metadata[rel_path] = {"hash": file_hash, "mtime": mtime}

print("Saving metadata and writing CSV log...")
with open(metadata_path, "w") as f:
    json.dump(mirror_metadata, f, indent=2)

with open(csv_log_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["File", "Status"])
    writer.writerows(log_entries)

if include_zip:
    print("Creating full zip backup...")
    status_by_file = {}
    file_list_for_zip = []

    for root_dir, _, files in os.walk(source_dir):
        for name in files:
            full_path = os.path.join(root_dir, name)
            if Path(full_path).name in EXCLUDED_FILES:
                continue
            file_list_for_zip.append(full_path)

    est_seconds = len(file_list_for_zip) * 0.02  # rough 20ms per file
    print(f"⏳ Estimated time for ZIP creation: ~{round(est_seconds, 1)} seconds")

    for full_path in file_list_for_zip:
        rel_path = os.path.relpath(full_path, source_dir)
        mtime = datetime.fromtimestamp(os.path.getmtime(full_path))
        if not zip_path.exists():
            status = "new"
        elif mtime > datetime.fromtimestamp(os.path.getmtime(zip_path)):
            status = "edited"
        else:
            status = "unchanged"
        status_by_file[rel_path] = (status, full_path)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        manifest = []
        for rel_path, (_, full_path) in status_by_file.items():
            print(f"Zipping file: {rel_path}")
            zipf.write(full_path, rel_path)
            manifest.append(rel_path)
        zipf.writestr("manifest.txt", "[Manifest created {}]\n{}".format(
            datetime.now().isoformat(), "\n".join(manifest)))

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["File", "Status"])
        for rel_path, (status, _) in sorted(status_by_file.items()):
            writer.writerow([rel_path, status])

    with open(log_path, "a") as f:
        f.write(f"\nBackup run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Backup file: {zip_path}\n")
        f.write(f"Files total: {len(status_by_file)}\n")
        f.write(f" - New: {sum(1 for s in status_by_file.values() if s[0] == 'new')}\n")
        f.write(f" - Edited: {sum(1 for s in status_by_file.values() if s[0] == 'edited')}\n")
        f.write(f" - Unchanged: {sum(1 for s in status_by_file.values() if s[0] == 'unchanged')}\n")
        if os.path.exists(zip_path):
            size_mb = round(os.path.getsize(zip_path) / (1024 * 1024), 2)
            f.write(f"ZIP size: {size_mb} MB\n")
        f.write(f"Status CSV: {csv_path}\n")
        f.write("-" * 40 + "\n")

duration = round(time.time() - start_time, 2)
print("\n✅ Sync complete!")
print(f"⏱️ Duration: {duration} seconds")
print(f"🆕 New: {sum(1 for _, s in log_entries if s == 'new')}")
print(f"✏️ Modified: {sum(1 for _, s in log_entries if s == 'modified')}")
print(f"✅ Unchanged: {sum(1 for _, s in log_entries if s == 'unchanged')}")
print(f"📄 Log saved to: {csv_log_path}")
print(f"📁 Files staged for upload: {to_upload_dir}")
if include_zip:
    print(f"📜 Full zip backup also created: {zip_path}")
