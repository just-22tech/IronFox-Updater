# 🦊 IronFox Auto-Updater

An automated bot that fetches the latest **IronFox** browser releases from GitLab, optimizes the **APKs structure**, and uploads it to your personal **Google Drive**. 

![Build Status](https://img.shields.io/github/actions/workflow/status/just-22tech/IronFox-Updater/update.yml?style=flat-square&label=Auto-Update)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square)
![Rclone](https://img.shields.io/badge/Powered%20by-Rclone-orange?style=flat-square)

## 🚀 Features

- **🔄 Auto-Sync:** Checks GitLab every 2 hours for new releases.
- **🧠 Smart Filter:** Extracts only `arm64-v8a` and `xxhdpi` resources (removes bloat).
- **📉 Size Optimization:** Automatically compares `master` split files, keeps the best one, and removes unnecessary architectures (x86, etc.).
- **☁️ Cloud Upload:** Uses **Rclone** to upload directly to Google Drive.
- **📂 History Mode:** Can store all previous versions or auto-clean old ones.

## 🛠️ How It Works

1. **Detect:** Scans GitLab API for new release tags.
2. **Check:** Verifies if the file already exists in your Google Drive.
3. **Process (In-Memory):** Downloads the latest `.apks`.
    - Deletes `toc.pb` and unused splits.
    - Repacks the optimized Zip.
4. **Upload:** Pushes the final file to your Drive folder.

## ⚙️ Setup Guide

### 1. Fork this Repository
Click the **Fork** button on the top right to make your own copy.

### 2. Configure Secrets
Go to `Settings` > `Secrets and variables` > `Actions` > `New repository secret`.

| Secret Name | Value |
|-------------|-------|
| `RCLONE_CONFIG` | Copy the full output of `rclone config show` (from `[gdrive]` to end). |

### 3. Update Settings
Edit the `config.json` file in your repo:

```json
{
  "gitlab_project_id": "65779408",
  "drive_folder_id": "YOUR_DRIVE_FOLDER_ID",
  "keep_old_versions": true
}