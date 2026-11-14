# LYA Phone Command Module

A secure, zero-paid-service remote trigger and monitor for your Windows laptop powered by Supabase (PostgreSQL + RLS + Storage) and a React PWA installable on iPhone.

- **No raw shell execution**: All actions are validated against an explicit local JSON allowlist (`config.json`).
- **Strict RLS**: Only authenticated users registered in the `admins` table can queue commands or inspect logs.
- **Atomic Server-Side Claims**: `claim_next_command()` atomically claims pending commands using `FOR UPDATE SKIP LOCKED`.
- **60-Second Replay & Expiry Guard**: Commands older than 60 seconds are automatically marked `rejected: expired`.
- **Private Screenshots**: Stored in a private Supabase bucket and viewed on iPhone using 60-second time-limited signed URLs.

---

## 1. Supabase Setup

1. Create a free project at [supabase.com](https://supabase.com).
2. Go to the **SQL Editor** in your Supabase dashboard and run the entire contents of [`schema.sql`](schema.sql).
3. Under **Authentication > Users**, create an admin user (e.g. your email and password). Copy the user's `User UID`.
4. Run this query in the SQL Editor to authorize your user:
   ```sql
   insert into public.admins (id, email)
   values ('<YOUR-USER-UUID>', '<YOUR-EMAIL>');
   ```
5. Retrieve your project keys from **Project Settings > API**:
   - `Project URL`
   - `anon public key`
   - `service_role secret key`

---

## 2. Laptop Listener Setup (Windows)

### A. Environment & Configuration
1. Open PowerShell in `phone-command/`:
   ```powershell
   cd phone-command
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env`:
   ```env
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_KEY=your-service-role-key
   ```
3. Copy `config.json.example` to `config.json` and configure your approved apps, websites, and scripts:
   ```json
   {
     "apps": {
       "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
       "notepad": "C:\\Windows\\System32\\notepad.exe"
     },
     "sites": {
       "github": "https://github.com"
     },
     "scripts": {
       "backup": "C:\\Users\\kathirvel\\backup.bat"
     }
   }
   ```
   *Note: Only `.exe`, `.bat`, and `.cmd` extensions are accepted for scripts. Any action not in `config.json` is strictly rejected.*

### B. Test the Listener Manually
Run:
```powershell
python listener.py
```
You will see it:
- Acquire the single-instance lock (`listener.lock`).
- Reconcile any previously interrupted commands.
- Publish allowed actions to Supabase with automatic backoff retry.
- Start writing logs to both the console and `listener.log` (1 MB rotating log with 3 backups).
- Poll every 2 seconds for new commands using `claim_next_command()`.

### C. Schedule with Windows Task Scheduler
To have the listener run silently in the background whenever you log into Windows:

1. Open **Task Scheduler** (`taskschd.msc`).
2. Click **Create Task...** (do not use Basic Task).
3. In the **General** tab:
   - **Name**: `LYA_Phone_Command_Listener`
   - Under *Security options*, choose **“Run only when user is logged on”**.
4. In the **Triggers** tab:
   - Click **New...**
   - Begin the task: **At log on** (choose your user account).
5. In the **Actions** tab:
   - Click **New...**
   - Action: **Start a program**
   - **Program/script**: Use `pythonw.exe` once file logging works, so it runs completely in the background without opening a command prompt window:
     ```text
     C:\Users\kathirvel\Downloads\lya-main\lya-main\phone-command\.venv\Scripts\pythonw.exe
     ```
   - **Add arguments**: `listener.py`
   - **Start in**:
     ```text
     C:\Users\kathirvel\Downloads\lya-main\lya-main\phone-command
     ```
6. In the **Conditions** tab:
   - Uncheck *"Start the task only if the computer is on AC power"*.
7. In the **Settings** tab:
   - Check *"If the task fails, restart every 1 minute"*.
8. Click **OK**.

You can verify it is running by checking `phone-command/listener.log`.

---

## 3. Deploy PWA to Vercel

1. Push your repository to GitHub (ensure `.env` and `config.json` remain ignored).
2. Go to [vercel.com](https://vercel.com) and import the repository.
3. Set the **Root Directory** to `phone-command/web`.
4. Under **Environment Variables**, add:
   - `VITE_SUPABASE_URL`: `https://your-project.supabase.co`
   - `VITE_SUPABASE_ANON_KEY`: `your-supabase-anon-key`
5. Click **Deploy**.

---

## 4. Install on iPhone Home Screen

1. Open the deployed Vercel URL in **Safari** on your iPhone.
2. Log in with your admin credentials.
3. Tap the **Share** button in Safari (box with arrow pointing up).
4. Scroll down and tap **Add to Home Screen**.
5. Tap **Add**. 
6. Open the **LYA Command** icon from your home screen — it runs standalone full-screen with instant action buttons, live execution status, and 60-second screenshot viewer.
