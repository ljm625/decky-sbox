export interface RunStatus {
  binary_version: string;
  online: boolean;
  config: string;
}

export interface Network {
  allowDNS: boolean;
  allowDefault: boolean;
  allowManaged: boolean;
  allowGlobal: boolean;
  assignedAddresses: string[];
  id: string;
  mac: string;
  name: string;
  portDeviceName: string;
  status: string;
  type: string;
}

export interface ConfigStatus {
  name: string;
  url: string;
  selected: boolean;
  valid: boolean;
}