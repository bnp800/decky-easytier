import { FaServer, FaNetworkWired, FaCheckCircle, FaTimesCircle, FaClock, FaExclamationTriangle } from 'react-icons/fa';
import { PanelSectionRow } from '@decky/ui';
import { CombinedStatus } from '../types';

interface DualStatusPanelProps {
  status: CombinedStatus;
}

export const DualStatusPanel: React.FC<DualStatusPanelProps> = ({ status }) => {
  const getStatusIcon = (state?: string) => {
    switch (state) {
      case 'running':
        return <FaCheckCircle className="color-success" />;
      case 'stopped':
        return <FaTimesCircle className="color-danger" />;
      case 'crashed':
      case 'error':
        return <FaExclamationTriangle className="color-warning" />;
      case 'starting':
      case 'partial':
        return <FaClock className="color-highlight" />;
      default:
        return null;
    }
  };

  const getStatusText = (state?: string) => {
    switch (state) {
      case 'running':
        return '运行中';
      case 'stopped':
        return '已停止';
      case 'crashed':
      case 'error':
        return '错误';
      case 'starting':
        return '启动中';
      case 'partial':
        return '部分运行';
      default:
        return '未知';
    }
  };

  return (
    <div className="dual-status-panel">
      <PanelSectionRow>
        <div className="status-row">
          <div className="status-item">
            <div className="status-icon">
              <FaServer />
            </div>
            <div className="status-info">
              <div className="status-label">Web管理控制台</div>
              <div className="status-value">
                {getStatusIcon(status.web_status)}
                <span>{getStatusText(status.web_status)}</span>
              </div>
            </div>
          </div>

          <div className="status-item">
            <div className="status-icon">
              <FaNetworkWired />
            </div>
            <div className="status-info">
              <div className="status-label">VPN节点服务</div>
              <div className="status-value">
                {getStatusIcon(status.core_status)}
                <span>{getStatusText(status.core_status)}</span>
              </div>
            </div>
          </div>
        </div>
      </PanelSectionRow>

      {status.overall === 'running' && (
        <PanelSectionRow>
          <div className="node-info">
            <div className="node-count">
              已连接节点数: <strong>{status.node_count || 1}</strong>
            </div>
            <div className="access-info">
              访问地址: <code>http://{status.ip}:11211</code>
            </div>
          </div>
        </PanelSectionRow>
      )}
    </div>
  );
};