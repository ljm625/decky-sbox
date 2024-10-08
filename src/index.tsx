import {
  PanelSection,
  PanelSectionRow,
  showModal,
  DialogButton,
  ShowModalResult,
  ToggleField,
  Navigation
} from "@decky/ui";

import { callable, definePlugin } from '@decky/api';

import { useEffect, useState } from "react";

import { ConfigStatus, RunStatus } from "./model";
import AddConfigModal from "./components/AddConfigModal";
import ConfigButton from "./components/ConfigButton";
import ConfigDetailModal from "./components/ConfigDetailModal";

const info = callable<[], RunStatus>("info");
const listConfigs = callable<[], ConfigStatus[]>("list_configs");
const setSingboxStatus = callable<[boolean]>("toggle_singbox");

/**
 * The main component of the plugin, responsible for displaying the service status and managing the network operations.
 *
 * @remarks
 * This component uses React hooks to manage state and perform side effects. It fetches the node status and network list
 * from the ZeroTier API, updates the state accordingly, and displays the information in a user-friendly format.
 * It also handles opening and closing modals for joining and viewing network details.
 *
 * @returns A React component that renders the plugin's content.
 */
function Content() {
  // State variables for storing node status, network list, and modal result
  const [runState, setRunState] = useState<RunStatus>({ binary_version: "", online: false, config: '' });
  const [configs, setConfigs] = useState<ConfigStatus[]>([]);
  const [modalResult, setModalResult] = useState<ShowModalResult | null>(null);

  // Fetch node status and network list from the ZeroTier API every 5 seconds
  useEffect(() => {
    const fetchData = async () => {
      info().then(response => {
        setRunState(response);
      });

      listConfigs().then(response =>{
        setConfigs(response.map(configs => configs as ConfigStatus));
      })

      // toaster.toast({title: "Connected to ZeroTier", body: "Version: " + nodeState.version})
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);

    // clean up the interval when the plugin is unmounted
    return () => clearInterval(interval);
  }, []);

  // Open the join network modal and update the modal result state
  const openAddModal = () => {
    const result = showModal(<AddConfigModal closeModal={closeModal} />);
    setModalResult(result);
  };

  // Open the network detail modal and update the modal result state
  const openDetailModal = (configs: ConfigStatus) => {
    const result = showModal(<ConfigDetailModal config={configs} closeModal={closeModal} />);
    setModalResult(result);
  };

  const handleRunStateOnChange = (status: boolean) => {
    setRunState(prevState => ({ ...prevState, online: status }));
    setSingboxStatus(status);
  };


  // Close the current modal and refresh the network list
  const closeModal = () => {
    modalResult?.Close();
    setModalResult(null);

    listConfigs().then(response =>{
      setConfigs(response.map(configs => configs as ConfigStatus));
    })
};

  // Render the plugin's content
  return (
    <div>
      <PanelSection title="Service">
        <PanelSectionRow>
          {"Sing-box: " + runState.binary_version}<br />
          {"Status: " + runState.online}<br />
          {"Config: " + runState.config}<br />
        </PanelSectionRow>
        <PanelSectionRow>
        <ToggleField label="Start Sing-box" disabled={runState.binary_version.length==0 || runState.config.length==0} checked={runState.online} onChange={(val) => handleRunStateOnChange(val)} />
        </PanelSectionRow>
        <PanelSectionRow>
        <DialogButton disabled={!runState.online} onClick={() =>{
            Navigation.NavigateToExternalWeb("http://127.0.0.1:9090/ui")
          }}>Open WebUI</DialogButton>
        </PanelSectionRow>
        <PanelSectionRow>
          <DialogButton onClick={openAddModal}>Add New Config Profile</DialogButton>
        </PanelSectionRow>
      </PanelSection>
      <PanelSection title="Profiles">
        {configs.map(cfg =>
          <PanelSectionRow>
            <ConfigButton config={cfg} onClick={() => openDetailModal(cfg)} />
          </PanelSectionRow>
        )}
      </PanelSection>
    </div>
  );
};

export default definePlugin(() => {

  return {
    name: "Decky ZeroTier",
    version: "0.0.1",
    content: <Content />,
    icon: <svg fill="currentColor" height="1em" width="1em" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M4.01 0A3.999 3.999 0 0 0 .014 4v16c0 2.209 1.79 4 3.996 4h15.98a3.998 3.998 0 0 0 3.996-4V4c0-2.209-1.79-4-3.996-4zm-.672 2.834h17.326a.568.568 0 1 1 0 1.137h-8.129c.021.059.033.123.033.19v1.804A6.06 6.06 0 0 1 18.057 12c0 3.157-2.41 5.75-5.489 6.037v2.56a.568.568 0 1 1-1.136 0v-2.56A6.061 6.061 0 0 1 5.943 12a6.06 6.06 0 0 1 5.489-6.035V4.16c0-.066.012-.13.033-.19H3.338a.568.568 0 1 1 0-1.136zm8.094 4.307A4.89 4.89 0 0 0 7.113 12a4.89 4.89 0 0 0 4.319 4.86zm1.136 0v9.718A4.892 4.892 0 0 0 16.888 12a4.892 4.892 0 0 0-4.32-4.86z" /></svg>,
  };
});
