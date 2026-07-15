#!/bin/sh

if test -e $HOME/homebrew/plugins/decky-sbox; then
    echo "decky-sbox exists"
    sudo rm -r $HOME/homebrew/plugins/decky-sbox
fi

if test -e /tmp/decky-sbox.zip; then
    sudo rm /tmp/decky-sbox.zip
fi

echo "Downloading Sbox..."
curl -L -o /tmp/decky-sbox.zip https://github.com/ljm625/decky-sbox/releases/download/v0.1.5/decky-sbox-v0.1.5.zip

if test ! -e $HOME/homebrew/plugins; then
    sudo mkdir -p $HOME/homebrew/plugins
fi
systemctl --user stop plugin_loader 2> /dev/null
sudo systemctl stop plugin_loader 2> /dev/null
sudo mkdir -p $HOME/homebrew/plugins/decky-sbox
sudo unzip /tmp/decky-sbox.tar.gz -d $HOME/homebrew/plugins
sudo rm /tmp/decky-sbox.zip

sudo systemctl start plugin_loader
echo "Decky-sbox is installed."