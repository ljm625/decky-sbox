import os
from os import W_OK, access, stat
from os.path import dirname
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from helpers import get_ssl_context # type: ignore
from settings import SettingsManager  # type: ignore
from pathlib import Path
import json
import asyncio
import re
from subprocess import CalledProcessError

# The decky plugin module is located at decky-loader/plugin
# For easy intellisense checkout the decky-loader code one directory up
# or add the `decky-loader/plugin` path to `python.analysis.extraPaths` in `.vscode/settings.json`
import decky

# Force LD_LIBRARY_PATH to include system paths for libssl
env = os.environ.copy()
env['LD_LIBRARY_PATH'] = '/usr/lib:/usr/lib64'

SB_BINARY = os.path.join(decky.DECKY_PLUGIN_DIR, 'bin', 'sing-box')
SB_BINARY_FOLDER = os.path.join(decky.DECKY_PLUGIN_DIR, 'bin')
SB_HOME = decky.DECKY_PLUGIN_SETTINGS_DIR

class Plugin:

    async def _main(self):
        decky.logger.info('Starting Decky-SBox...')

        self.settings = SettingsManager(name="deckysbox", settings_directory=decky.DECKY_PLUGIN_SETTINGS_DIR)
        enabled = self.get_setting("enable",False)
        if enabled:
            decky.logger.info('Starting Sing-box on startup...')
            await self.start_singbox()
        else:
            decky.logger.info('Stop Sing-box on startup...')
            await self.stop_singbox()



    # @staticmethod
    # async def zerotier_cli(command: list[str]) -> tuple[bytes, bytes]:
    #     """
    #     Executes the ZeroTier-CLI command with the provided arguments.

    #     Parameters:
    #     command (list[str]): A list of strings representing the command and its arguments.

    #     Returns:
    #     tuple[bytes, bytes]: A tuple containing the standard output and standard error of the command.

    #     Raises:
    #     CalledProcessError: If the ZeroTier-CLI command returns a non-zero exit code.
    #     """
    #     cmd = [SB_BINARY, '-q', '-j', f'-D{SB_HOME}', *command]

    #     proc = await asyncio.create_subprocess_exec(
    #         *cmd,
    #         stdout=asyncio.subprocess.PIPE,
    #         stderr=asyncio.subprocess.STDOUT,
    #         env=env
    #     )
        
    #     stdout, stderr = await proc.communicate()

    #     if proc.returncode == 0:
    #         decky.logger.info(' '.join(cmd))
    #         decky.logger.info(f'ZeroTier-CLI exited with code {proc.returncode}')
    #         decky.logger.info(stdout.decode('utf-8'))
    #     else:
    #         decky.logger.error(f'ZeroTier-CLI exited with code {proc.returncode}')
    #         decky.logger.error(stdout.decode('utf-8'))
    #         raise CalledProcessError(proc.returncode, cmd, stdout=stdout, stderr=stderr)

    #     return stdout, stderr


    @staticmethod
    async def _read_stream(stream, cb):
        """
        Reads a stream line by line and calls a callback function with each line.

        This function is designed to be used with asyncio's StreamReader objects, such as those returned by
        asyncio.subprocess.PIPE. It reads the stream line by line, decodes the bytes to a UTF-8 string, strips
        leading/trailing whitespace, and then calls the provided callback function with the decoded line.

        Parameters:
        stream (asyncio.StreamReader): The stream to read from.
        cb (callable): A function that takes a single string argument. This function will be called for each
                        line read from the stream.

        Returns:
        None
        """
        while True:
            line = await stream.readline()
            if line:
                cb(line.decode('utf-8').strip())
            else:
                break
    
    async def info(self) -> dict:
        running = False
        if not os.path.exists(SB_BINARY):
            version = await self.check_and_extract_singbox()
        else:
            version = self.get_setting("version","")
            for x in os.popen('pgrep sing-box'):
                if x:
                    running = True
                    break
        use_config = self.get_setting("use_config","")
        return {"binary_version":version,"online":running,"config":use_config}

    async def list_configs(self) -> list:
        configs = self.get_setting("configs",{})
        use_config = self.get_setting("use_config","")
        resp = []
        for name,detail in configs.items():
            tmp = {
                "name": name,
                "url": detail["url"],
                "selected": True if use_config==name else False,
                "valid": True,
            }
            resp.append(tmp)
        return resp

    async def refresh_config(self,config_name: str) -> bool:
        configs = self.get_setting("configs",{})
        cur_in_use_config = self.get_setting("use_config","")
        if configs.get(config_name):
            result = await self.download_file(configs[config_name]["url"],SB_HOME,"{}.json".format(config_name))
            decky.logger.info(f'Refreshed config {configs[config_name]["url"]} {result}')
            if result:
                if cur_in_use_config==config_name:
                    # We need to restart sing-box
                    pass
                return True
        return False
    
    async def delete_config(self,config_name: str) -> bool:
        configs = self.get_setting("configs",{})
        cur_in_use_config = self.get_setting("use_config","")
        if configs.get(config_name):
            if os.path.exists(Path(SB_HOME) / "{}.json".format(config_name)):
                os.remove(Path(SB_HOME) / "{}.json".format(config_name))
                decky.logger.info(f'Removed config {Path(SB_HOME) / "{}.json".format(config_name)}')
                configs.pop(config_name,None)
                self.set_setting("configs",configs)
                if cur_in_use_config==config_name:
                    # We need to stop sing-box then delete
                    self.set_setting("use_config","")
                    pass
                return True
        return False

    async def update_config(self,config_name: str,config_key: str, config_value) -> bool:
        configs = self.get_setting("configs",{})
        cur_in_use_config = self.get_setting("use_config","")
        if configs.get(config_name):
            if config_key=="selected":
                selected = config_value
                if selected and cur_in_use_config!=config_name:
                    # We switched select status
                    cur_in_use_config = config_name
                    self.set_setting("use_config",cur_in_use_config)
                    # We need to restart sing-box to take effect
                elif not selected and cur_in_use_config==config_name:
                    cur_in_use_config=""
                    self.set_setting("use_config",cur_in_use_config)
                    # We need to stop sing-box to take effect
            decky.logger.info(f'Updated config {config_name} {config_key} -> {config_value}')
            return True
        return False


    async def download_config(self,config_name: str, config_url: str) -> bool:
        configs = self.get_setting("configs",{})
        decky.logger.info(f'config settings {configs}')
        cur_in_use_config = self.get_setting("use_config","")


        result = await self.download_file(config_url,SB_HOME,"{}.json".format(config_name))
        decky.logger.info(f'Downloaded config {config_url} {result}')
        if result:
            configs[config_name]={"url":config_url}
            self.set_setting("configs",configs)
            if cur_in_use_config=="":
                self.set_setting("use_config",config_name)
            decky.logger.info(f'config settings after update {configs}')
            return True
        return False
    
    def parse_and_modify_config(self,config_name) -> bool:
        log_config={
            "level": "warn",
            "timestamp": True
        }
        webui_config={
            "external_controller": "127.0.0.1:9090",
            "external_ui": os.path.join(SB_HOME,"web"),
            "secret": "",
            "default_mode": "rule"
        }
        tun_config={
        "type": "tun",
        "tag": "tun-in",
        "interface_name": "tun0",
        "address": [
            "172.18.0.1/30",
            "fdfe:dcba:9876::1/126"
        ],
        "mtu": 9000,
        "gso": True,
        "auto_route": True,
        "strict_route": True,
        "route_address": [
            "0.0.0.0/1",
            "128.0.0.0/1",
            "::/1",
            "8000::/1"
        ],
        "route_exclude_address": [
            "192.168.0.0/16",
            "fc00::/7"
        ],
        "stack": "system",
        "platform": {
            "http_proxy": {
                "enabled": False,
                "server": "127.0.0.1",
                "server_port": 8080,
                "bypass_domain": [],
                "match_domain": []
            }
        }
        }

        if os.path.exists(os.path.join(SB_HOME,f'{config_name}.json')):
            config_info = {}
            try:
                with open(os.path.join(SB_HOME,f'{config_name}.json'),"r") as file:
                    config_info=json.load(file)
            except Exception as e:
                decky.logger.error(f"config file open fail: {os.path.join(SB_HOME,f'{config_name}.json')} {e.msg}")
                return False
            config_info["log"]=log_config
            if not config_info.get("experimental"):
                config_info["experimental"]={}
            config_info["experimental"]["clash_api"]=webui_config
            if not config_info.get("inbounds"):
                config_info["inbounds"]={}
            modify_pos = -1
            for i in range(0,len(config_info["inbounds"])):
                if config_info["inbounds"][i]["type"]=="tun":
                    modify_pos = i
                    break
            if modify_pos>=0:
                config_info["inbounds"][modify_pos]=tun_config
            else:
                config_info["inbounds"].append(tun_config)
            with open(os.path.join(SB_HOME,f'running_config.json'),"w") as file:
                json.dump(config_info,file)
            decky.logger.info(f"Modified config save to: {os.path.join(SB_HOME,f'running_config.json')}")
            return True
        return False
    
    async def check_and_extract_singbox(self) -> str:
        extracted = False
        if not os.path.exists(SB_BINARY):
            files = os.listdir(SB_BINARY_FOLDER)
            for file_name in files:
                if re.match(r'^sing-box.*amd64\.tar\.gz$',file_name):
                    decky.logger.info(f"tar xzvf {os.path.join(SB_BINARY_FOLDER,file_name)} --strip-components=1 -C {SB_BINARY_FOLDER}")
                    proc = await asyncio.create_subprocess_exec(
                        "tar", "xzvf", os.path.join(SB_BINARY_FOLDER,file_name),"--strip-components=1", "-C", SB_BINARY_FOLDER,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                        env=env
                    )
                    await proc.communicate()
                    extracted = True
                    break
        if os.path.exists(SB_BINARY):
            if extracted:
                # Update version in settings
                output = os.popen(f"{SB_BINARY} version")
                for line in output:
                    result = re.search(r"sing-box version (.+)",line)
                    if result:
                        version = result[1].strip()
                        self.set_setting("version",version)
                        decky.logger.info(f"Sing Box version: {version}")
                        return version

    async def start_singbox(self) -> bool:
        if not os.path.exists(SB_BINARY):
            await self.check_and_extract_singbox()
        if os.path.exists(SB_BINARY):
            cur_in_use_config = self.get_setting("use_config","")
            if cur_in_use_config:
                result =self.parse_and_modify_config(cur_in_use_config)
                if result:
                    proc = await asyncio.create_subprocess_exec(
                        "nohup", SB_BINARY,"run","-D",SB_HOME,"-c", os.path.join(SB_HOME,f'running_config.json'),"&",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                        env=env
                    )
                    # os.popen(f"nohup {SB_BINARY} run -c {os.path.join(SB_HOME,f'running_config.json')} &")
                    return True
        else:
            decky.logger.info("Couldn't find sing-box binary")
            return False
        return False
    async def stop_singbox(self):
        for pid in os.popen('pgrep sing-box'):
            if pid:
                os.popen(f'kill {pid}')
                return True
        return False
    
    async def toggle_singbox(self,status):
        if status == True:
            await self.stop_singbox()
            await self.start_singbox()
        elif status == False:
            await self.stop_singbox()
        self.set_setting("enable",status)
    
    async def download_file(self, url='', output_dir='', file_name=''):
        decky.logger.debug({url, output_dir, file_name})
        try:
            if access(dirname(output_dir), W_OK):
                req = Request(url, headers={'User-Agent': 'sing-box'})
                res = urlopen(req, context=get_ssl_context())
                if res.status == 200:
                    with open(Path(output_dir) / file_name, mode='wb') as f:
                        f.write(res.read())
                    return str(Path(output_dir) / file_name)
                return False
        except:
            return False

        return False

    # async def info(self) -> dict:
    #     """
    #     Retrieves information about the ZeroTier network interface.

    #     This function executes the ZeroTier-CLI command with the 'info' argument and returns the parsed JSON response.
    #     The JSON response contains various details about the ZeroTier network interface.
    #     {
    #         "address": "8ad1b*****",
    #         "clock": 1722903840676,
    #         "config": {
    #             "settings": {
    #                 "allowTcpFallbackRelay": true,
    #                 "forceTcpRelay": false,
    #                 "homeDir": "/home/deck/homebrew/settings/decky-zerotier",
    #                 "listeningOn": [],
    #                 "portMappingEnabled": true,
    #                 "primaryPort": 9993,
    #                 "secondaryPort": 28820,
    #                 "softwareUpdate": "disable",
    #                 "softwareUpdateChannel": "release",
    #                 "surfaceAddresses": [],
    #                 "tertiaryPort": 23494
    #             }
    #         },
    #         "online": false,
    #         "planetWorldId": 1496*****,
    #         "planetWorldTimestamp": 1644592324813,
    #         "publicIdentity": "8ad1b5d1a4:0:5be4396e895539bcd221491*********************************************************************************************************",
    #         "tcpFallbackActive": false,
    #         "version": "1.14.0",
    #         "versionBuild": 0,
    #         "versionMajor": 1,
    #         "versionMinor": 14,
    #         "versionRev": 0
    #     }

    #     Parameters:
    #     None

    #     Returns:
    #     dict: A dictionary containing the parsed JSON response from the ZeroTier-CLI 'info' command.

    #     Raises:
    #     CalledProcessError: If the ZeroTier-CLI command returns a non-zero exit code.
    #     """
    #     stdout, _ = await self.zerotier_cli(['info'])
    #     return json.loads(stdout.decode('utf-8'))


    # async def list_networks(self) -> list[dict]:
    #     """
    #     Retrieves a list of ZeroTier networks and their configurations.

    #     This function executes the ZeroTier-CLI 'listnetworks' command, and merges it with the ZT_NETCONF file. 
    #     If the ZT_NETCONF file exists, it adds any missing networks with a 'DISCONNECTED' status.
    #     Finally written back to the ZT_NETCONF file.

    #     [{
    #         "allowDNS": false,
    #         "allowDefault": false,
    #         "allowGlobal": false,
    #         "allowManaged": true,
    #         "assignedAddresses": ["10.10.0.***/24"],
    #         "bridge": false,
    #         "broadcastEnabled": true,
    #         "dhcp": false,
    #         "dns": {
    #         "domain": "",
    #         "servers": []
    #         },
    #         "id": "48d6023*********",
    #         "mac": "da:05:ab:**:**:**",
    #         "mtu": 2800,
    #         "multicastSubscriptions": [{
    #             "adi": 0,
    #             "mac": "01:00:5e:**:**:**"
    #         }],
    #         "name": "GamingRoom",
    #         "netconfRevision": 20,
    #         "nwid": "48d6023*********",
    #         "portDeviceName": "ztos******",
    #         "portError": 0,
    #         "routes": [{
    #             "flags": 0,
    #             "metric": 0,
    #             "target": "10.10.0.0/24",
    #             "via": null
    #         }],
    #         "status": "OK",
    #         "type": "PUBLIC"
    #     }]

    #     Parameters:
    #     None

    #     Returns:
    #     list[dict]: A list of dictionaries, where each dictionary represents a ZeroTier network. Each dictionary
    #             contains the following keys: 'id', 'name', 'private', 'status', and 'routes'.

    #     Raises:
    #     CalledProcessError: If the ZeroTier-CLI command returns a non-zero exit code.
    #     """
    #     stdout, _ = await self.zerotier_cli(['listnetworks'])
    #     networks = json.loads(stdout.decode('utf-8'))

    #     if os.path.exists(SB_CONF):
    #         with open(SB_CONF, 'r') as f:
    #             netconf = []

    #             try:
    #                 netconf = json.load(f)
    #             except json.JSONDecodeError:
    #                 decky.logger.warning('Invalid JSON in networks conf')

    #             for net in netconf:
    #                 if net['id'] not in [n['id'] for n in networks]:
    #                     net['status'] = 'DISCONNECTED'
    #                     networks.append(net)

    #     with open(SB_CONF, 'w') as f:
    #         json.dump(networks, f)
            
    #     return networks
    

    # async def disconnect_network(self, network_id: str) -> list[dict]:
    #     """
    #     Disconnects from a ZeroTier network with the specified network ID.

    #     This function executes the ZeroTier-CLI 'leave' command with the provided network ID.
    #     And save the network with 'DISCONNECTED' status to the local network configuration file (ZT_NETCONF).

    #     Parameters:
    #     network_id (str): The ID of the ZeroTier network to disconnect from.

    #     Returns:
    #     list[dict]: Same as the `list_networks` method.

    #     Raises:
    #     CalledProcessError: If the ZeroTier-CLI command returns a non-zero exit code.
    #     """
    #     networks = await self.list_networks()
    #     stdout, _ = await self.zerotier_cli(['leave', network_id])
    #     decky.logger.info(f'Left network {network_id}: {stdout.decode("utf-8").strip()}')

    #     networks_ = []
    #     for net in networks:
    #         if net['id'] == network_id:
    #             net['status'] = 'DISCONNECTED'
    #         networks_.append(net)

    #     with open(SB_CONF, 'w') as f:
    #         json.dump(networks, f)
        
    #     return networks
    
    # async def forget_network(self, network_id: str) -> list[dict]:
    #     """
    #     Forgets a ZeroTier network with the specified network ID.

    #     This function executes the ZeroTier-CLI 'leave' command with the provided network ID,
    #     and removes the network from the local network configuration file (ZT_NETCONF).

    #     Parameters:
    #     network_id (str): The ID of the ZeroTier network to forget.

    #     Returns:
    #     list[dict]: A list of dictionaries, where each dictionary represents a ZeroTier network. Each dictionary
    #                 contains the following keys: 'id', 'name', 'private', 'status', and 'routes'.

    #     Raises:
    #     CalledProcessError: If the ZeroTier-CLI command returns a non-zero exit code.
    #     """
    #     stdout, _ = await self.zerotier_cli(['leave', network_id])
    #     decky.logger.info(f'Forgotten network {network_id}: {stdout.decode("utf-8").strip()}')

    #     if os.path.exists(SB_CONF):
    #         with open(SB_CONF, 'r') as f:
    #             netconf = json.load(f)
    #         netconf_ = [net for net in netconf if net['id']!= network_id]
    #         with open(SB_CONF, 'w') as f:
    #             json.dump(netconf_, f)

    #     return await self.list_networks()
    
    # async def update_network(self, network_id: str, option: str, value: bool) -> list[dict]:
    #     """
    #     Updates a specific network configuration option for a ZeroTier network.

    #     This function executes the ZeroTier-CLI 'set' command with the provided network ID, option, and value.

    #     Parameters:
    #     network_id (str): The ID of the ZeroTier network to update.
    #     option (str): The network configuration option to update. 
    #         'allowDNS': Allow DNS Configuration
    #         'allowDefault':Allow Default Router Override
    #         'allowManaged: Allow Managed Address
    #         'allowGlobal':Allow Assignment of Global IPs
    #     value (bool): The new value for the specified network configuration option.

    #     Returns:
    #     list[dict]: Same as the `list_networks` method.

    #     Raises:
    #     CalledProcessError: If the ZeroTier-CLI command returns a non-zero exit code.
    #     """
    #     stdout, _ = await self.zerotier_cli(['set', network_id, f'{option}={int(value)}'])
    #     decky.logger.info(f'Update network {network_id}: {stdout.decode("utf-8").strip()}')

    #     return await self.list_networks()
        
    # # Asyncio-compatible long-running code, executed in a task when the plugin is loaded
    # async def _main(self) -> None:
    #     decky.logger.info('Starting ZeroTier...')

    #     cmd = [ZT_ONE, ZT_HOME]
    #     decky.logger.info(' '.join(cmd))
        
    #     self.process = await asyncio.create_subprocess_exec(
    #         *cmd,
    #         stdout=asyncio.subprocess.PIPE,
    #         stderr=asyncio.subprocess.STDOUT,
    #         env=env
    #     )

    #     await self._read_stream(self.process.stdout, decky.logger.info)
        
    #     self.process.wait()


    # Function called first during the unload process, utilize this to handle your plugin being stopped, but not
    # completely removed
    async def _unload(self) -> None:
        decky.logger.info('Stopping SingBox...')


    # Function called after `_unload` during uninstall, utilize this to clean up processes and other remnants of your
    # plugin that may remain on the system
    async def _uninstall(self) -> None:
        self._unload()
        decky.logger.info('Uninstalling decky-sbox...')
        # TODO: Clean up your plugin's resources here
        pass

    # Migrations that should be performed before entering `_main()`.
    def set_setting(self, key, value):
        self.settings.setSetting(key, value)

    def get_setting(self, key, fallback):
        return self.settings.getSetting(key, fallback)

    async def _migration(self):
        decky.migrate_settings(str(Path(decky.DECKY_HOME) / "settings" / "deckysbox.json"))