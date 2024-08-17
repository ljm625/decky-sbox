import { callable, toaster } from "@decky/api";
import { ConfirmModal, DialogBody, Focusable, TextField, Field } from "@decky/ui";
import { Network } from "../model";
import { useState } from "react";

const AddConfigModal: React.FC<{ closeModal: () => void }> = ({ closeModal }) => {
  const downloadConfig = callable<[string], boolean>("download_config");
  const [configName, setConfigName] = useState<string>("config");
  const [netID, setNetID] = useState<string>("abcde");
  const [bOKDisabled, setBOKDisabled] = useState<boolean>(true);
  
  const handleOnChange = () => {
    if( netID.trim().startsWith("http") && configName.trim().length>0){
      setBOKDisabled(false)
    } else{
      setBOKDisabled(true)
    }
  }


  return (
    <ConfirmModal
      strTitle="Enter config name and url..."
      strDescription="Please enter the sing-box config/subscribe url."
      strOKButtonText="Download"
      bOKDisabled={bOKDisabled}
      onCancel={closeModal}
      onOK={() => {
        downloadConfig(netID)
        toaster.toast({ title: "Downloading configuration...", body: netID });
        closeModal();
      }}

    >
      <DialogBody>
        <Focusable>
         <Field label='Config Name' bottomSeparator='none' />
          <TextField
            spellCheck="false"
            onChange={(evt) => {
              setConfigName(evt.target.value);
              handleOnChange();
            }}
            value = {configName}
          />
          <Field label='Config Url' bottomSeparator='none' />
          <TextField
            spellCheck="false"
            onChange={(evt) => {
              setNetID(evt.target.value);
              handleOnChange();
            }}
          />
        </Focusable>
      </DialogBody>
    </ConfirmModal>
  )
}

export default AddConfigModal;