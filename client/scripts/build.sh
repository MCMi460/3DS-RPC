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
python3 -m pip install -U -r requirements.txt py2app # Install requirements + py2app
cp -R ../api ./api # Kind of hacky method to get API w/o sys path hack
py2applet --make-setup app.py "icon.png" # Make setup.py
sed -i '' -e "s/)/    name='3DS-RPC')/" setup.py # Update app name
python3 setup.py py2app -O2 --packages=IPython,pygments # Build
#                           (Also I'm not sure if removing the packages thing works or not.
#                           I've been at this for four hours now and I'm too scared to
#                           touch it now that it's finally working. Sorry.)
rm -rf ./api # Remove module
open dist # Open for user's benefit
