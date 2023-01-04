cd ..

# Delete previous build files
if [ -d ./build/ ]
then
  rm -rf ./build/
fi
if [ -d ./dist/ ]
then
  rm -rf ./dist/
fi
if [ -e ./setup.py ]
then
  rm ./setup.py
fi

# Actual building
python3 -m pip install -U -r requirements.txt pyinstaller # Install requirements + pyinstaller
cp -R ../api ./api # Kind of hacky method to get API w/o sys path hack
pyinstaller client.py --onefile # Pretty much just package Python into an executable with our program
rm -rf ./api # Remove module
open dist # Open for user's benefit
