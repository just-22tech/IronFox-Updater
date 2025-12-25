import os
import json
import zipfile
import requests
import io
import subprocess
import shutil

# Load Configuration
with open('config.json', 'r') as f:
    config = json.load(f)

GITLAB_PROJECT_ID = config['gitlab_project_id']
GITLAB_URL = config['gitlab_url']
DRIVE_FOLDER_ID = config['drive_folder_id'] # Note: Rclone uses Folder ID directly or Path
KEEP_OLD_VERSIONS = config['keep_old_versions']
FILE_PREFIX = config['file_prefix']

# Rclone remote name (Must match what we configure in YAML)
REMOTE_NAME = "gdrive" 

def run_rclone(args):
    """Helper to run rclone commands"""
    result = subprocess.run(['rclone'] + args, capture_output=True, text=True)
    return result

def get_latest_gitlab_release():
    print("Checking GitLab for latest release...")
    url = f"{GITLAB_URL}/api/v4/projects/{GITLAB_PROJECT_ID}/releases"
    response = requests.get(url, timeout=60)
    if response.status_code != 200:
        print(f"Failed to fetch releases. Status: {response.status_code}")
        return None
    
    releases = response.json()
    if not releases:
        return None
    
    latest_release = releases[0]
    tag_name = latest_release['tag_name']
    
    target_asset = None
    for asset in latest_release['assets']['links']:
        if asset['name'].startswith(FILE_PREFIX) and asset['name'].endswith('.apks'):
            target_asset = asset
            break
            
    if not target_asset:
        print(f"No .apks file found in release {tag_name}")
        return None
        
    return {
        'tag': tag_name,
        'filename': target_asset['name'],
        'url': target_asset['url']
    }

def check_file_in_drive(filename):
    print(f"Checking if {filename} exists in Drive...")
    # Check if file exists in the specific folder ID
    # Syntax: rclone lsf remote,id=FOLDERID:filename
    cmd = ['lsf', f"{REMOTE_NAME},root_folder_id={DRIVE_FOLDER_ID}:{filename}"]
    result = run_rclone(cmd)
    
    # If output contains the filename, it exists
    return filename in result.stdout

def upload_to_drive(local_path, filename):
    print(f"Uploading {filename} via Rclone...")
    # Copy file to the specific folder ID
    cmd = ['copy', local_path, f"{REMOTE_NAME},root_folder_id={DRIVE_FOLDER_ID}:"]
    result = run_rclone(cmd)
    
    if result.returncode == 0:
        print("Upload Successful!")
        return True
    else:
        print(f"Upload Failed: {result.stderr}")
        return False

def clean_drive_old_versions(current_filename):
    print("Cleaning up old versions...")
    
    # List all files matching prefix
    cmd = ['lsf', f"{REMOTE_NAME},root_folder_id={DRIVE_FOLDER_ID}:", '--include', f"{FILE_PREFIX}*.apks"]
    result = run_rclone(cmd)
    files = result.stdout.splitlines()
    
    for f in files:
        if f != current_filename:
            print(f"Deleting old version: {f}")
            del_cmd = ['deletefile', f"{REMOTE_NAME},root_folder_id={DRIVE_FOLDER_ID}:{f}"]
            run_rclone(del_cmd)

def process_file(asset):
    print(f"Downloading {asset['filename']}...")
    r = requests.get(asset['url'], timeout=60)
    input_zip_data = io.BytesIO(r.content)
    
    # Temporary output file
    output_filename = asset['filename']
    
    print("Processing APKS content...")
    with zipfile.ZipFile(input_zip_data, 'r') as zin:
        with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zout:
            file_list = zin.namelist()
            
            # Master file logic
            master_files = {}
            for f in file_list:
                if 'base-master' in f:
                    master_files[f] = zin.getinfo(f).file_size
            
            best_master = None
            if master_files:
                best_master = max(master_files, key=master_files.get)
                print(f"Selected Master File: {best_master}")

            for item in zin.infolist():
                filename = item.filename
                
                # Filter Logic
                if 'toc.pb' in filename: continue
                
                if filename.startswith('splits/'):
                    if 'base-xxhdpi.apk' in filename or 'base-arm64_v8a.apk' in filename:
                        zout.writestr(item, zin.read(filename))
                        continue
                    if filename == best_master:
                        zout.writestr(item, zin.read(filename))
                        continue
                    continue
                
                zout.writestr(item, zin.read(filename))
                
    print("File processed and saved locally.")
    return output_filename

def main():
    # 1. Check GitLab
    release_info = get_latest_gitlab_release()
    if not release_info:
        return

    # 2. Check Drive (Rclone)
    if check_file_in_drive(release_info['filename']):
        print(f"File {release_info['filename']} already exists in Drive. Exiting.")
        return

    # 3. Process
    local_file = process_file(release_info)

    # 4. Upload (Rclone)
    if upload_to_drive(local_file, release_info['filename']):
        # 5. Cleanup
        if not KEEP_OLD_VERSIONS:
            clean_drive_old_versions(release_info['filename'])
            
    # Remove local file
    if os.path.exists(local_file):
        os.remove(local_file)

if __name__ == '__main__':
    main()