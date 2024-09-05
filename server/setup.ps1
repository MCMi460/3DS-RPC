# Define variables for commonly used paths
$VenvDir = ".\venv"
$AnyNetRepo = "https://github.com/MCMi460/anynet"
$NintendoClientsRepo = "https://github.com/kinnay/NintendoClients"
$StaticDir = ".\static"
$TemplatesDir = ".\templates"
$DbFile = ".\sqlite\fcLibrary.db"

# Set up a Python virtual environment
if (Test-Path $VenvDir) {
    Remove-Item -Recurse -Force $VenvDir
}
python -m venv venv
& .\venv\Scripts\Activate.ps1

# Clone and install anynet
git clone "$AnyNetRepo" -b w/o-netifaces2
Set-Location -Path "anynet"
python -m pip install .
Set-Location -Path ".."
Remove-Item -Recurse -Force "anynet"

# Clone and install NintendoClients
git clone $NintendoClientsRepo
Set-Location -Path "NintendoClients"
python -m pip install .
Set-Location -Path ".."
Remove-Item -Recurse -Force "NintendoClients"

Set-Location -Path "server"

# Install additional Python dependencies
python -m pip install -r requirements.txt
python -m pip install -U Flask-SQLAlchemy


# Build static files with npm
if (Test-Path $StaticDir) {
    Remove-Item -Recurse -Force $StaticDir
}
Set-Location -Path $TemplatesDir
if (Test-Path ".\dist") {
    Remove-Item -Recurse -Force ".\dist"
}
npm install
npm run build

# Finally, end script
Write-Output "Script ended"
