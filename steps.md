# Python Project Setup

### 1. Install Python 3.12 if it doesn't exist

```bash
brew install python@3.12
```

### 2. Create and activate the virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Install packages

```bash
pip install -r requirements.txt
```

### Black Formatter

Usage and Features
(View > Command Palette... and run Preferences: Open User Settings (JSON)):
"[python]": {
"editor.defaultFormatter": "ms-python.black-formatter",
"editor.formatOnSave": true
}
