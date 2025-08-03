# DigitalOcean Droplet Connection Guide

## Current Status
- **Droplet Name**: droplet1
- **Droplet ID**: 511013276
- **IP Address**: 134.199.206.143
- **Status**: Active
- **Region**: Atlanta 1
- **Size**: s-1vcpu-2gb-amd

## SSH Key Mismatch Issue
Your local SSH key (`droplet1` / `droplet1.pub`) does NOT match the key currently authorized on the droplet.

- **Droplet's authorized key**: dropletkey (fingerprint: 96:f2:3d:62:6d:2c:72:cb:cb:6c:77:72:07:be:b9:fe)
- **Your local key**: Different key (not currently authorized)

## How to Connect

### Option 1: Add your key via DigitalOcean Console (Recommended)
1. Log into [DigitalOcean Console](https://cloud.digitalocean.com)
2. Navigate to your droplet
3. Click "Access" → "Launch Droplet Console"
4. In the console, run:
   ```bash
   mkdir -p ~/.ssh && chmod 700 ~/.ssh
   echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEqPQcVAch/fCBv8NAV+YLO86FkAJnpsBGBth2nke5N7 canaan@OASIS" >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```
5. Then you can SSH from your local machine:
   ```bash
   ssh -i droplet1 root@134.199.206.143
   ```

### Option 2: Reset Root Password
1. Run: `python3 manage_droplet_ssh.py` (uncomment the password reset section)
2. Check your email for the new root password
3. SSH with password: `ssh root@134.199.206.143`
4. Add your SSH key manually

### Option 3: Find the Original Private Key
The droplet is configured with a different SSH key ("dropletkey"). If you have the private key for that, use it instead.

## Quick SSH Command
Once your key is authorized:
```bash
./ssh_connect.sh
# or directly:
ssh -i droplet1 root@134.199.206.143
```