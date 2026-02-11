import { Field } from '@decky/ui';
import { FaServer, FaNetworkWired } from 'react-icons/fa';
import { CombinedStatus, ProcessStatus } from '../types';

interface DualStatusPanelProps {
  status: CombinedStatus;
}

const STATUS_LABELS: Record<ProcessStatus, string> = {
  running: '运行中',
  stopped: '已停止',
  crashed: '已崩溃',
  error: '错误',
};

const getStatusText = (state?: ProcessStatus): string =>
  state ? STATUS_LABELS[state] ?? '未知' : '未知';

export const DualStatusPanel: React.FC<DualStatusPanelProps> = ({ status }) => {
  return (
    <>
      <Field
        label="Web 控制台"
        icon={<FaServer />}
      >
        {getStatusText(status.web_status)}
      </Field>
      <Field
        label="VPN 节点"
        icon={<FaNetworkWired />}
      >
        {getStatusText(status.core_status)}
      </Field>
    </>
  );
};
