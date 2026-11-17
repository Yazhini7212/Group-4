# Getting Started (for beginners, with VS Code)

How to get the code, share changes, run it on the RWTH cluster, and use Jupyter notebooks,
all from **VS Code**.

**The idea:** you edit code on your laptop *or* directly on the cluster through VS Code.
The data (~50 GB) lives **only on the cluster**, so notebooks that look at images run there.

---

## 1. One-time setup on your laptop

1. **GitHub account:** sign up at https://github.com and send your username to Yazhini.
2. **Accept the invite:** check your email, or open
   https://github.com/Yazhini7212/Group-4/invitations and click *Accept*.
   Without this you can download the code but not upload changes.
3. **Install:**
   * Git: https://git-scm.com/downloads (default options)
   * VS Code: https://code.visualstudio.com
   * Python 3.11 or newer: https://www.python.org/downloads (Windows: tick *Add python.exe to PATH*)
4. **Tell Git who you are.** In VS Code: **Terminal → New Terminal**, then type
   (use your GitHub email):
   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   ```

## 2. Get the code into VS Code (once)

1. In VS Code press **Ctrl+Shift+P**, type **Git: Clone**, press Enter.
2. Paste `https://github.com/Yazhini7212/Group-4.git` and pick a folder (e.g. *Documents*).
3. Click **Open** when VS Code asks.
4. A pop-up offers the **recommended extensions** (Python, Jupyter, Remote-SSH, Rainbow CSV).
   Click **Install**.
5. Make the Python environment: **Ctrl+Shift+P → Python: Create Environment → Venv**, pick your
   Python, and **tick `requirements.txt`**. VS Code creates a `.venv` folder and installs
   everything. This takes a few minutes, and you only do it once.

## 3. Daily routine: download changes, upload yours

Use the **Source Control** tab on the left (the icon with three dots joined by lines), or
**Ctrl+Shift+G**.

| Step | In VS Code | Same thing in the terminal |
|---|---|---|
| **Get teammates' changes** (always first) | ⋯ menu → **Pull** | `git pull` |
| See what you changed | changed files are listed in Source Control | `git status` |
| Select changes | **+** next to a file (or next to *Changes* for all) | `git add .` |
| Save a snapshot | type a message in the box → **Commit** | `git commit -m "Add hashing"` |
| **Upload** | **Sync Changes** / **Push** | `git push` |

The first push opens a GitHub sign-in in your browser. Sign in with the invited account.

**If uploading fails:**
* *"rejected… fetch first"* → a teammate pushed first. **Pull**, then **Push** again.
* *"Permission denied / 403"* → you haven't accepted the invite, or you signed in with
  another GitHub account.

**Group rules**
* Pull before you start, push when you finish, and say so in the group chat.
* Never upload data, images or `kaggle.json`. The `.gitignore` file blocks most of it.
* Clear notebook outputs before committing (see section 6).
* Write messages others understand: "Add perceptual hash", not "stuff".

---

## 4. Connect VS Code to the RWTH cluster

1. Click the green **><** button in the bottom-left corner → **Connect to Host…** →
   **+ Add New SSH Host…** and type:
   ```
   ssh <your-TIM-ID>@login23-1.hpc.itc.rwth-aachen.de
   ```
   If that address doesn't work, look up the current login nodes on
   https://help.itc.rwth-aachen.de (search "CLAIX login"). You may be asked for a second-factor code.
2. Connect again via **><** and pick the host. Enter your password. VS Code is now *on the cluster*:
   the terminal, files and notebooks all run there.
3. **First time only**, in a VS Code terminal (on the cluster):
   ```bash
   git clone https://github.com/Yazhini7212/Group-4.git
   cd Group-4
   bash scripts/hpc/setup_env.sh
   ```
   Then **File → Open Folder → `Group-4`**.

## 5. Kaggle token and data download (once, on the cluster)

1. On https://www.kaggle.com → your picture → **Settings → API → Create New Token**.
   A file `kaggle.json` downloads to your laptop.
2. Drag `kaggle.json` from your laptop into the VS Code file explorer (connected to the
   cluster). Then in the terminal:
   ```bash
   mkdir -p ~/.kaggle && mv kaggle.json ~/.kaggle/ && chmod 600 ~/.kaggle/kaggle.json
   ```
3. Accept the RSNA rules once:
   https://www.kaggle.com/competitions/rsna-pneumonia-detection-challenge/rules
4. Start the download as a **job**. It takes hours and runs even when you close VS Code:
   ```bash
   sbatch scripts/hpc/download.sbatch
   squeue -u $USER          # PD = waiting, R = running, gone = finished
   ```
   Its output is written to the `logs/` folder. Open the file in VS Code to read it.
5. After it finishes, make the small working copies:
   ```bash
   sbatch scripts/hpc/cache.sbatch --limit 100   # quick test
   sbatch scripts/hpc/cache.sbatch               # full run
   ```

Data ends up in `$HPCWORK/chest_overlap`. Normally only **one** person downloads. Agree in the
group whose folder is used, and check that the others can read it.

---

## 6. Jupyter notebooks

Notebooks (`.ipynb`) mix code, results and pictures. They're the easiest way to explore the data.
Ours live in the `notebooks/` folder. Start with `notebooks/01_explore_data.ipynb`.

**Open and run**
1. Click the notebook in the VS Code explorer.
2. Top right: **Select Kernel → Jupyter Kernel… → `chest_overlap`**
   (on your laptop: **Python Environments → `.venv`**).
3. Run a cell with **Shift+Enter**. Run everything with **Run All** in the toolbar.

**Where to run them**
* **On the cluster (VS Code connected via section 4):** notebooks can see the real data.
  Use this to look at images and results.
* **On your laptop:** fine for editing, and for trying code on small examples. There is no data
  there, so the image cells just print "no data yet".

**Using our code in a notebook**
```python
from chest_overlap import load_index, show_rows
df = load_index(["nih"])          # the NIH table
show_rows(df.sample(4))           # show 4 random images
```
The first cell prints the data folder in use. If it isn't your `$HPCWORK/chest_overlap`,
add this line to the top of the notebook:
```python
import os; os.environ["CHEST_OVERLAP_DATA"] = "/path/to/chest_overlap"
```

**Rules for notebooks**
* Notebooks are for **looking** at data. Long jobs (download, cache, matching all images)
  go through `sbatch`, not a notebook. Notebooks on a login node get stopped if they run
  too long or use too much memory.
* **Before committing:** toolbar **⋯ → Clear All Outputs**, then save. Outputs (images)
  make the file huge and cause merge conflicts.
* Don't edit someone else's notebook at the same time as them. Make your own copy
  (`02_yourname_topic.ipynb`).

---

## 7. Cheat sheet

| I want to… | Do this |
|---|---|
| get the newest code | Source Control → ⋯ → **Pull** |
| upload my work | **+** → message → **Commit** → **Sync/Push** |
| connect to the cluster | green **><** bottom-left → your host |
| start the data download | `sbatch scripts/hpc/download.sbatch` |
| see my jobs / cancel one | `squeue -u $USER` / `scancel <job number>` |
| open a notebook | click it → **Select Kernel → chest_overlap** |
| run a cell | **Shift+Enter** |
| before committing a notebook | **⋯ → Clear All Outputs** → save |

Want to understand the code itself? Read the [code manual](MANUAL.md).
