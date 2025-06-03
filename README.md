# SyncOnedriveApp

A lightweight macOS app to stage your local folders for manual OneDrive syncing. It mirrors newly created and changed files to a `to_upload` folder and optionally zips your entire source folder into a compressed archive. Designed for users who may be unable or prohibited from having Onedrive Sync locally on their MAC OS and want a smart, version-aware backup and file tracking system to aid in manually uploading new and edited files to OneDrive.

---

## 📁 Folder Structure

```
SyncOnedriveApp/
├── appLauncher/             # Contains Automator .app to launch the backup
├── sourceCode/              # Python script to run the backup logic
├── localDataSync/           # Automatically created during first run
│   ├── to_upload/           # Files staged for upload
│   ├── uploadLogs/          # Daily CSV logs of sync status
│   ├── metaData/            # Stores JSON metadata and config
│   │   └── onedrive_mirror_metadata.json
│   │   └── source_directory.json
│   ├── onedrive_backup_latest.zip  # Full ZIP archive (optional)
│   ├── backup_log.txt              # Cumulative ZIP backup log
│   └── backup_status_YYYY-MM-DD.csv  # ZIP status snapshot
```

---

## ✅ Features

- Detects **new** and **modified** files based on hash and modified time.
- Skips large directories that haven't changed.
- Optionally zips entire folder (for archival or upload).
- Excludes known junk files like `.DS_Store`, `Thumbs.db`, and hidden `._` files.
- Remembers your selected source folder across runs.
- CSV logs of each session.
- GUI prompts using AppleScript for minimal interface.

---

## 🚀 How to Use

1. **Clone or download** the repo.

2. Open `SyncOnedriveApp/appLauncher/SyncOnedriveApp.app`.

3. On first run, you'll be prompted to:
   - Select a parent folder (defaults to `~/Documents`).
   - Choose between appending/updating or replacing files.
   - Decide whether to include a ZIP backup.

4. Your staged files will appear in:

   ```
   SyncOnedriveApp/localDataSync/to_upload
   ```

5. After verifying, manually drag these files to your OneDrive folder.

6. Optional: After syncing with Onedrive through your browser, delete all files within the `to_upload` folder. Alternatively, you will be prompted to clear the folder next time the app is executed. 

---

## 🔐 .gitignore

Make sure to exclude your own sensitive or large test files during development:

```
# Ignore local data from test runs
localDataSync/
```

---

## ⚙️ Requirements

- macOS (Tested on Monterey and Ventura)
- Python 3.9+
- No external dependencies

---

## 🛠 Developer Notes

- Folder hashes aren't stored—only file hashes and mtimes.
- ZIP creation gives a rough time estimate.
- App is Automator-based, but all logic runs in Python.

---

## 📬 Feedback & Contributions

Pull requests are welcome! If you'd like to add notifications, smarter exclusion filters, or OneDrive API integration, feel free to open an issue or PR.

---

### 🔐 Granting Permission if You See “App is Damaged”

macOS may block the app the first time you open it with:

> “SyncFilesApp” is damaged and can’t be opened.

To bypass:

1. Open **Terminal** manually
2. Navigate to the app folder, e.g.:

```bash
cd ~/Documents/SyncFilesApp
```

3. Then run:

```bash
xattr -r -d com.apple.quarantine ./appLauncher/SyncFilesApp.app
```

Now try launching it again:

```bash
open ./appLauncher/SyncFilesApp.app
```

---
