import { FaRegSquareCheck, FaRegSquare, FaRegSquareMinus, FaGear } from 'react-icons/fa6';

import { ConfigStatus } from '../model';
import { DialogButton, Field } from '@decky/ui';
const NetworkStatusIcon: React.FC<{ status: boolean }> = ({ status }) => {
  const size = 20;

  switch (status) {
    case true:
      return <FaRegSquareCheck size={size} />;
    case false:
      return <FaRegSquare size={size} />;
    default:
      return <FaRegSquareMinus size={size} />;
  }
};

/**
 * A React functional component that renders a network button with a status icon and a configuration button.
 *
 * @param network - The network object containing information about the network.
 * @param onClick - A callback function that will be called when the configuration button is clicked.
 *
 * @returns A React element representing the network button.
 */
const ConfigButton: React.FC<{ config: ConfigStatus, onClick: () => void }> = ({ config, onClick }) => {
  const name = config.name ? config.name : config.selected;

  return (
    <Field
      label={<>
        <style>{`.dz-network-label { padding: 0px; margin: 0px; } .dz-network-label > div:nth-of-type(2) { margin-top: 4px; }`}</style>
        <Field label={name} description={config.url} className='dz-network-label' bottomSeparator='none' />
      </>}
      icon={<NetworkStatusIcon status={config.selected} />}
      childrenLayout='inline'
    >
      <DialogButton onClick={onClick} style={{ minWidth: 'unset', padding: '10px', lineHeight: '12px' }}>
        <FaGear />
      </DialogButton>
    </Field>
  )
};

export default ConfigButton;