import { callable, toaster } from "@decky/api";
import { ConfirmModal, DialogBody, Focusable, TextField, Field } from "@decky/ui";
import { useState } from "react";

const AddConfigModal: React.FC<{ closeModal: () => void }> = ({ closeModal }) => {
  const downloadConfig = callable<[string,string], boolean>("download_config");
  const [configName, setConfigName] = useState<string>("config");
  const [configURL, setConfigURL] = useState<string>("abcde");
  const [bOKDisabled, setBOKDisabled] = useState<boolean>(true);
  
  const handleOnChange = () => {
    if( configURL.trim().startsWith("http") && configName.trim().length>0){
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
        downloadConfig(configName,configURL)
        toaster.toast({ title: "Downloading configuration...", body: configURL });
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
              setConfigURL(evt.target.value);
              handleOnChange();
            }}
          />
        </Focusable>
      </DialogBody>
    </ConfirmModal>
  )
}

export default AddConfigModal;