# Getting Started (for beginners)

Short and simple: how to get the code, share your changes, and run it on the RWTH cluster.
Type the grey commands into a terminal (Windows: **Git Bash**; Mac/Linux: **Terminal**).

---

## 1. One-time setup on your laptop

1. **Make a GitHub account** at https://github.com and send your username to Yazhini.
2. **Accept the invite**: you get an email, or open
   https://github.com/Yazhini7212/Group-4/invitations and click *Accept*.
   (Without this, you can download the code but not upload.)
3. **Install Git**: https://git-scm.com/downloads (keep the default options).
4. **Tell Git who you are** (use the email of your GitHub account):
   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   ```

## 2. Download the code (only once)

Go to the folder where you want the project, then "clone" (= download) it:
```bash
cd ~/Documents
git clone https://github.com/Yazhini7212/Group-4.git
cd Group-4
```
You now have a `Group-4` folder with all the code.

## 3. Every time you start working: get the latest version

```bash
cd ~/Documents/Group-4
git pull
```
Always do this first, so you have your teammates' newest changes.

## 4. Upload your changes

After editing or adding files:
```bash
git status                       # see what changed
git add .                        # select all changes
git commit -m "Short note of what I did"
git push                         # upload to GitHub
```
The first `git push` opens a GitHub sign-in window. Sign in with the account that was invited.

**If `git push` is refused:**
* `rejected … fetch first` → someone uploaded before you. Run `git pull`, then `git push` again.
* `Permission denied` / `403` → your account isn't a collaborator yet (see step 1.2), or you
  signed in with a different GitHub account.

**Rules for the group**
* Never upload data, images or your `kaggle.json` (the `.gitignore` file blocks most of it).
* Pull before you start, push when you finish, and tell the group in chat.
* Write commit messages others can understand: `"Add perceptual hash"`, not `"stuff"`.

---

## 5. Running it on the RWTH cluster

The datasets are ~50 GB, so they are downloaded **on the cluster**, never on your laptop.

### 5.1 Log in (from your laptop's terminal)
```bash
ssh <your-TIM-ID>@login23-1.hpc.itc.rwth-aachen.de
```
If that address doesn't work, check the current login addresses in the RWTH HPC documentation
(https://help.itc.rwth-aachen.de); you may also be asked for a second-factor code.

### 5.2 First time only
```bash
git clone https://github.com/Yazhini7212/Group-4.git
cd Group-4
bash scripts/hpc/setup_env.sh
```

**Kaggle token** (lets the cluster download the data for you):
1. Log in at https://www.kaggle.com → click your picture → **Settings** → **API** →
   **Create New Token**. A file `kaggle.json` downloads to your laptop.
2. Copy it to the cluster (run this **on your laptop**, not the cluster):
   ```bash
   scp kaggle.json <your-TIM-ID>@login23-1.hpc.itc.rwth-aachen.de:~/
   ```
3. Back **on the cluster**:
   ```bash
   mkdir -p ~/.kaggle && mv ~/kaggle.json ~/.kaggle/ && chmod 600 ~/.kaggle/kaggle.json
   ```
4. Open https://www.kaggle.com/competitions/rsna-pneumonia-detection-challenge/rules and
   click **I Understand and Accept** (needed for the RSNA dataset).

### 5.3 Download the data (runs as a job, takes hours)
```bash
cd ~/Group-4
git pull
sbatch scripts/hpc/download.sbatch
```

### 5.4 Check on your job
```bash
squeue -u $USER                 # is it waiting (PD) or running (R)?
ls logs/                        # find the log file
tail -f logs/cxr_download_*.out # watch the output live (Ctrl+C to stop watching)
```

### 5.5 Make the small working copies (after the download finished)
```bash
sbatch scripts/hpc/cache.sbatch --limit 100   # quick test on 100 images per dataset
sbatch scripts/hpc/cache.sbatch               # then the full run
```

The data ends up in `$HPCWORK/chest_overlap` (see it with `ls $HPCWORK/chest_overlap`).
Only **one** person needs to download it if the group shares that folder. Agree on whose
`$HPCWORK` to use first.

---

## 6. Cheat sheet

| I want to… | Command |
|---|---|
| get the code the first time | `git clone https://github.com/Yazhini7212/Group-4.git` |
| get the newest changes | `git pull` |
| see what I changed | `git status` |
| upload my changes | `git add .` → `git commit -m "…"` → `git push` |
| log in to the cluster | `ssh <TIM-ID>@login23-1.hpc.itc.rwth-aachen.de` |
| start the data download | `sbatch scripts/hpc/download.sbatch` |
| see my running jobs | `squeue -u $USER` |
| cancel a job | `scancel <job number>` |

Want to understand what the code does? Read the [code manual](MANUAL.md).
