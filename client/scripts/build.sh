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

# Actual building
python3 -m pip install -U -r requirements.txt py2app # Install requirements + py2app
cp -R ../api ./api # Kind of hacky method to get API w/o sys path hack
python3 setupMac.py py2app -O2 # Build
rm -rf ./api # Remove module
open dist # Open for user's benefit
