import { callable } from "@decky/api";
import { ConfirmModal, DialogSubHeader, Field, ToggleField } from "@decky/ui";
import { ConfigStatus } from "../model";
import { useState } from "react";

export interface ConfigDetailModalProps {
  config: ConfigStatus;
  closeModal: () => void;
}

/**
 * A modal component that displays detailed information and settings for a ZeroTier network.
 *
 * @param network - The network object to display information for.
 * @param closeModal - A function to be called when the modal should be closed.
 * @returns A React functional component that renders the modal.
 */
const ConfigDetailModal: React.FC<ConfigDetailModalProps> = ({ config, closeModal }) => {
  const refreshConfig = callable<[configName: string], boolean>("refresh_config");
  const deleteConfig = callable<[configName: string], boolean>("delete_config");
  const updateConfig = callable<[configName: string, configKey:string, configValue: boolean], boolean>("update_config");

  const [configs, setConfigs] = useState<ConfigStatus>(config);

  /**
   * Handles changes to network options and updates the network state.
   *
   * @param option - The network option to update. {allowDNS, allowDefault, allowManaged, allowGlobal}
   * @param value - The new value for the network option.
   */
  const handleOnChange = (option: string, value: boolean) => {
    setConfigs(prevState => ({ ...prevState, [option]: value }));
    updateConfig(configs.name,option,value);
  }

  if (configs.selected === false) {
    return (
      <ConfirmModal
        strTitle={configs.name}
        strOKButtonText="Update"
        strMiddleButtonText="Delete"
        onOK={() => {
          refreshConfig(configs.name);
          // toaster.toast({ title: "Connecting network...", body: net.id });
          closeModal();
        }}
        onMiddleButton={() => {
          deleteConfig(configs.name);
          // toaster.toast({ title: "Forgetting network...", body: net.id });
          closeModal();
        }}
        onCancel={closeModal}
      >
      <ToggleField label="Use" disabled={configs.valid !==true} checked={configs.selected} onChange={(val) => handleOnChange("selected", val)} />
      </ConfirmModal>
    )
  } else {
    return (
      <ConfirmModal
        strTitle={configs.name}
        strOKButtonText="Delete"
        onOK={() => {
          deleteConfig(configs.name);
          closeModal();
        }}
        strCancelButtonText="Close"
        onCancel={closeModal}
      >
        <DialogSubHeader style={{ textTransform: "none" }}>
          {"URL: " + configs.url}<br />
          {"Valid: " + configs.valid}<br />
        </DialogSubHeader>
        <ToggleField label="Use" disabled={configs.valid !==true} checked={configs.selected} onChange={(val) => handleOnChange("selected", val)} />
        {/* <ToggleField label="Allow DNS Configuration" disabled={net.status !== "OK"} checked={net.allowDNS} onChange={(val) => handleOnChange("allowDNS", val)} />
        <ToggleField label="Allow Default Router Override" disabled={net.status !== "OK"} checked={net.allowDefault} onChange={(val) => handleOnChange("allowDefault", val)} />
        <ToggleField label="Allow Assignment of Global IPs" disabled={net.status !== "OK"} checked={net.allowGlobal} onChange={(val) => handleOnChange("allowGlobal", val)} /> */}
      </ConfirmModal>
    )
  }
};

export default ConfigDetailModal;