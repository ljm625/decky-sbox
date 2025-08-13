#!/bin/sh

if test -e $HOME/homebrew/plugins/decky-sbox; then
    echo "decky-sbox exists"
    sudo rm -r $HOME/homebrew/plugins/decky-sbox
fi

if test -e /tmp/decky-sbox.zip; then
    sudo rm /tmp/decky-sbox.zip
fi

echo "Downloading Sbox..."
latest_tag = $(curl -s https://api.github.com/repos/ljm625/decky-sbox/releases/latest | jq -r '.tag_name')
curl -L -o /tmp/decky-sbox.tar.gz https://github.com/ljm625/decky-sbox/archive/refs/tags/$latest_tag.tar.gz

if test ! -e $HOME/homebrew/plugins; then
    sudo mkdir -p $HOME/homebrew/plugins
fi
systemctl --user stop plugin_loader 2> /dev/null
sudo systemctl stop plugin_loader 2> /dev/null
mkdir -p $HOME/homebrew/plugins/decky-sbox
tar xzvf decky-sbox.tar.gz --strip-components=1 -C $HOME/homebrew/plugins/decky-sbox
sudo rm /tmp/decky-sbox.zip

sudo systemctl start plugin_loader
echo "Decky-sbox is installed."