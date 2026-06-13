I will answer your two questions clearly, then provide a **clean, step‑by‑step documentation** that you can reuse on any Windows machine.

---

## 1. How to remove testing data (products, sales, debtors, services, logs)

You want to keep the **core structure** (users, categories, service types, etc.) but delete all the test transactions.

### Safe cleanup script (run once after cloning)

Create a file `cleanup_test_data.py` in your project folder with this content:

```python
"""
Run this to delete all test data but keep:
- users (user1, user2, owner...)
- categories (Electronics, Drinks, Clothes, Curtains)
- service_categories (Repair, Installation, etc.)
- service_types (Laptop Repair, etc.)
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'localpos.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Delete all product-related data
cursor.execute("DELETE FROM sale_items")
cursor.execute("DELETE FROM sales")
cursor.execute("DELETE FROM debtors")
cursor.execute("DELETE FROM payments")
cursor.execute("DELETE FROM stock_entries")
cursor.execute("DELETE FROM products")
cursor.execute("DELETE FROM service_history")
cursor.execute("DELETE FROM service_jobs")
cursor.execute("DELETE FROM activity_log")

# Reset auto-increment counters
cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('products','sales','debtors','stock_entries','service_jobs','activity_log')")

conn.commit()
conn.close()
print("✅ All test data removed. Products, sales, debtors, services, and activity logs are cleared.")
```

Run it:

```bash
cd C:\Users\c\POS\LocalPOS
venv\Scripts\activate
python cleanup_test_data.py
```

Then restart the service (`nssm restart LocalPOS`). Your system will now be empty of test transactions, ready for real business.

> **Warning:** This deletes **all** products, sales, debtors, service jobs, and activity logs. Keep a backup if you need the data.

---

## 2. Step‑by‑step deployment documentation (for Windows 10)

Create a file named `DEPLOY.md` in your project folder. Copy the text below. You can then use it on any new machine.

```markdown
# LocalPOS – Windows Deployment Guide (with NSSM + Tailscale)

## Prerequisites
- Windows 10/11
- Administrator access
- Internet connection for first setup

---

## Step 1 – Install required software

### 1.1 Python
- Download from [python.org](https://www.python.org/downloads/) (version 3.11 or newer)
- **During installation**: check **“Add Python to PATH”**
- After installation, open **Command Prompt** and verify:
  ```cmd
  python --version
  ```

### 1.2 Git (optional, for cloning)
- Download from [git-scm.com](https://git-scm.com/download/win)
- Install with default options

### 1.3 NSSM (Windows service manager)
- Open PowerShell **as Administrator** and run:
  ```powershell
  winget install --source=winget --id=NSSM.NSSM
  ```
- If winget fails, download `nssm.exe` from [nssm.cc](https://nssm.cc/download) and place it in `C:\Windows\System32`

### 1.4 Tailscale (remote access)
- Download from [tailscale.com/download/windows](https://tailscale.com/download/windows)
- Install and **sign in** with your Google/Microsoft account (the owner’s account)

---

## Step 2 – Get the code

Open **Command Prompt** and run:

```cmd
cd /d C:\
mkdir POS
cd POS
git clone https://github.com/krypt-69/LocalPOS.git
cd LocalPOS
```

(If you don’t use Git, download the ZIP from GitHub and extract to `C:\POS\LocalPOS`)

---

## Step 3 – Set up Python environment

```cmd
cd /d C:\POS\LocalPOS
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
pip install waitress
```

---

## Step 4 – Initialise the database

```cmd
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database ready')"
```

---

## Step 5 – (Optional) Remove testing data

If you want a clean start (no example products or sales), create `cleanup_test_data.py` as shown above and run:

```cmd
python cleanup_test_data.py
```

---

## Step 6 – Create the batch file to run the app

```cmd
(
echo @echo off
echo cd /d C:\POS\LocalPOS
echo call venv\Scripts\activate
echo python -c "from waitress import serve; from app import app; serve(app, host='0.0.0.0', port=5000)"
) > run_localpos.bat
```

---

## Step 7 – Register the Windows service

```cmd
nssm stop LocalPOS
nssm remove LocalPOS confirm
nssm install LocalPOS "C:\Windows\System32\cmd.exe" "/c C:\POS\LocalPOS\run_localpos.bat"
nssm set LocalPOS AppDirectory C:\POS\LocalPOS
nssm set LocalPOS Start SERVICE_AUTO_START
nssm start LocalPOS
nssm status LocalPOS
```

The last command should output `SERVICE_RUNNING`.

---

## Step 8 – Test locally

Open a browser on the same machine and go to `http://localhost:5000`  
Login with `user1` / `password123` (or your owner account).

---

## Step 9 – Configure Tailscale for remote access

1. On the Windows machine, open **Tailscale** and ensure you are **logged in**.
2. Enable **MagicDNS**:  
   - Click the Tailscale icon in system tray → **Settings** → **DNS** → toggle **Use MagicDNS**.
3. Note the **machine name** (run `hostname` in Command Prompt).  
   Example: `SHOP-PC`
4. On your **phone or laptop**, also install Tailscale and log into the **same account**.
5. Open a browser on the remote device and go to:
   ```
   http://SHOP-PC:5000
   ```
   (Replace `SHOP-PC` with your actual computer name)

You can now manage the shop from anywhere, securely.

---

## Step 10 – Automatic startup after reboot

The service is already set to `SERVICE_AUTO_START`. To verify:

```cmd
nssm get LocalPOS Start
```

It should print `SERVICE_AUTO_START`. Reboot the machine, then check that the website is available.

---

## Troubleshooting

- **Service not starting**: Check logs with `nssm get LocalPOS AppStdout` and `nssm get LocalPOS AppStderr`. Then open the log files.
- **Tailscale not resolving name**: Run `tailscale ping SHOP-PC` – if it fails, use the Tailscale IP address shown in the app.
- **Port 5000 already in use**: Stop other services using that port, or change the port in `run_localpos.bat` (change `5000` to another number).

---

## Updating the code

- Stop the service: `nssm stop LocalPOS`
- Pull new code: `git pull` (or copy new files)
- Restart: `nssm start LocalPOS`

---

## Backup recommendation

- **Database**: Copy `C:\POS\LocalPOS\database\localpos.db` daily to an external drive or cloud.
- **Product images**: Back up `C:\POS\LocalPOS\static\uploads\products` if you use images.

---

Now your system is production‑ready. Use this guide on any new machine. Let me know if you need any adjustments.# LocalPOS
